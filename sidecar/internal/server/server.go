// Package server memuat server HTTP sidecar: `/api/health`, `/api/chat`
// (aliran teks UTF-8), dan penyajian berkas statis untuk renderer serta
// model besar.
//
// Ini adalah port dari `packages/server-runtime/src/http.ts`.
package server

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/daffa-789/ai-vtuber/sidecar/internal/agent"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/character"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/config"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/inference"
)

var mime = map[string]string{
	".html": "text/html; charset=utf-8",
	".js":   "text/javascript; charset=utf-8",
	".css":  "text/css; charset=utf-8",
	".json": "application/json",
	".wasm": "application/wasm",
	".onnx": "application/octet-stream",
	".png":  "image/png",
	".wav":  "audio/wav",
}

// HealthResponse adalah bentuk balasan `/api/health` yang dibaca renderer.
type HealthResponse struct {
	OK       bool     `json:"ok"`
	Model    string   `json:"model"`
	Cadangan []string `json:"cadangan"`
	Key      bool     `json:"key"`
	Tts      string   `json:"tts"`
	Stt      struct {
		Hidup  bool   `json:"hidup"`
		Model  string `json:"model"`
		Siap   bool   `json:"siap"`
		Alasan string `json:"alasan"`
	} `json:"stt"`
	Memori string `json:"memori"`
	Sisi   string `json:"sisi"`
}

// Opsi adalah seluruh masukan yang dibutuhkan handler sidecar.
type Opsi struct {
	Konfig     *config.Konfig
	Agent      *agent.Agent
	Provider   inference.Provider
	Vault      *character.CharacterVault
	ModelName  string
	StaticRoot string // folder hasil build renderer; kosong bila dev server Vite
	AssetRoot  string // folder model besar yang disajikan di bawah /assets/
}

type handler struct{ o Opsi }

func (h *handler) ServeHTTP(res http.ResponseWriter, req *http.Request) {
	aturCors(res)
	if req.Method == http.MethodOptions {
		res.WriteHeader(http.StatusNoContent)
		return
	}
	if err := h.rute(res, req); err != nil {
		var terlalu *terlaluBesar
		if errors.As(err, &terlalu) {
			tulisJson(res, http.StatusRequestEntityTooLarge, map[string]string{"error": err.Error()})
			return
		}
		tulisJson(res, http.StatusServiceUnavailable, map[string]string{"error": err.Error()})
	}
}

func (h *handler) rute(res http.ResponseWriter, req *http.Request) error {
	switch {
	case req.URL.Path == "/api/health" && req.Method == http.MethodGet:
		return h.health(res, req)
	case req.URL.Path == "/api/chat" && req.Method == http.MethodGet:
		tulisJson(res, http.StatusMethodNotAllowed, map[string]string{"error": "gunakan POST untuk /api/chat"})
		return nil
	case req.URL.Path == "/api/chat" && req.Method == http.MethodPost:
		return h.chat(res, req)
	case req.Method == http.MethodGet && strings.HasPrefix(req.URL.Path, "/assets/") && h.o.AssetRoot != "":
		if sajiStatis(res, h.o.AssetRoot, strings.TrimPrefix(req.URL.Path, "/assets")) {
			return nil
		}
	case req.Method == http.MethodGet && strings.HasPrefix(req.URL.Path, "/models/") && h.o.AssetRoot != "":
		if sajiStatis(res, filepath.Join(h.o.AssetRoot, "live2d"), strings.TrimPrefix(req.URL.Path, "/models")) {
			return nil
		}
	case req.Method == http.MethodGet && req.URL.Path == "/live2dcubismcore.min.js" && h.o.AssetRoot != "":
		if sajiStatis(res, filepath.Join(h.o.AssetRoot, "live2d"), "/live2dcubismcore.min.js") {
			return nil
		}
	case req.Method == http.MethodGet && h.o.StaticRoot != "" && !strings.HasPrefix(req.URL.Path, "/api/"):
		if sajiStatis(res, h.o.StaticRoot, req.URL.Path) {
			return nil
		}
		// Fallback SPA untuk navigasi renderer Electron.
		if sajiStatis(res, h.o.StaticRoot, "/index.html") {
			return nil
		}
	}
	tulisJson(res, http.StatusNotFound, map[string]string{"error": "tidak ditemukan"})
	return nil
}

func (h *handler) health(res http.ResponseWriter, req *http.Request) error {
	baik, alasan := h.o.Provider.Available(req.Context())
	model := h.o.ModelName
	if !baik {
		model = fmt.Sprintf("%s/tidak-jalan (%s)", model, alasan)
	}
	memori := h.o.Vault.UnavailableReason()
	if h.o.Vault.Available() {
		memori = "memori lokal (silver_wolf_memory/)"
	}
	isi := HealthResponse{OK: true, Model: model, Cadangan: []string{}, Key: true,
		Tts: "belum tersedia (Fase 3)", Memori: memori, Sisi: "go"}
	isi.Stt.Hidup = h.o.Konfig.SttHidup
	isi.Stt.Model = h.o.Konfig.SttModel
	isi.Stt.Siap = false
	isi.Stt.Alasan = "belum tersedia (Fase 2)"
	tulisJson(res, http.StatusOK, isi)
	return nil
}

type terlaluBesar struct{ error }

// RapikanRiwayat menyaring riwayat mentah dari klien menjadi pesan valid.
func RapikanRiwayat(mentah interface{}, maksPesan, maksKarakter int) []inference.Message {
	daftar, ok := mentah.([]interface{})
	if !ok {
		return nil
	}
	hasil := make([]inference.Message, 0, len(daftar))
	for _, item := range daftar {
		rekam, ok := item.(map[string]interface{})
		if !ok {
			continue
		}
		isi := ""
		if s, ok := rekam["content"].(string); ok {
			isi = s
		}
		if isi == "" {
			if bagian, ok := rekam["parts"].([]interface{}); ok {
				kumpulan := make([]string, 0, len(bagian))
				for _, p := range bagian {
					if rekamP, ok := p.(map[string]interface{}); ok {
						if teks, ok := rekamP["text"]; ok {
							kumpulan = append(kumpulan, fmt.Sprint(teks))
						}
					}
				}
				isi = strings.Join(kumpulan, " ")
			}
		}
		if strings.TrimSpace(isi) == "" {
			continue
		}
		peran := "user"
		if r, ok := rekam["role"].(string); ok && (r == "assistant" || r == "model") {
			peran = "assistant"
		}
		if len(isi) > maksKarakter {
			isi = isi[:maksKarakter]
		}
		hasil = append(hasil, inference.Message{Role: peran, Content: isi})
	}
	if len(hasil) > maksPesan {
		hasil = hasil[len(hasil)-maksPesan:]
	}
	return hasil
}

func (h *handler) chat(res http.ResponseWriter, req *http.Request) error {
	badan := http.MaxBytesReader(res, req.Body, int64(h.o.Konfig.MaksBody))
	mentah, err := io.ReadAll(badan)
	if err != nil {
		if strings.Contains(err.Error(), "http: request body too large") {
			return &terlaluBesar{errors.New("body terlalu besar")}
		}
		return err
	}
	var parsed struct {
		Messages interface{} `json:"messages"`
	}
	if err := json.Unmarshal(mentah, &parsed); err != nil {
		tulisJson(res, http.StatusBadRequest,
			map[string]string{"error": "body harus JSON: { messages: [{role, content}] }"})
		return nil
	}
	pesan := RapikanRiwayat(parsed.Messages, h.o.Konfig.MaksPesan, h.o.Konfig.MaksKarakter)
	if len(pesan) == 0 {
		tulisJson(res, http.StatusBadRequest, map[string]string{"error": "riwayat kosong"})
		return nil
	}
	aliran := h.o.Agent.Chat(req.Context(), pesan, inference.GenerateOptions{MaxTokens: 512, Temperature: 0.7})
	// Pacu token pertama sebelum 200 agar kegagalan boot masih dapat menjadi 503.
	pertama, terbuka := <-aliran
	if !terbuka {
		return errors.New("provider tidak menghasilkan apa pun")
	}
	if pertama.Err != nil {
		return pertama.Err
	}
	res.Header().Set("content-type", "text/plain; charset=utf-8")
	res.Header().Set("cache-control", "no-store")
	res.Header().Set("x-accel-buffering", "no")
	res.Header().Set("x-model", h.o.ModelName)
	res.WriteHeader(http.StatusOK)
	if _, err := io.WriteString(res, pertama.Text); err != nil {
		return nil
	}
	if perapi, ok := res.(http.Flusher); ok {
		perapi.Flush()
	}
	for potongan := range aliran {
		if potongan.Err != nil {
			return potongan.Err
		}
		if _, err := io.WriteString(res, potongan.Text); err != nil {
			return nil
		}
		if perapi, ok := res.(http.Flusher); ok {
			perapi.Flush()
		}
	}
	return nil
}

// ───────────────────────── berkas statis ─────────────────────────

// sajiStatis mengirim satu berkas dari root; false bila tidak ada.
func sajiStatis(res http.ResponseWriter, root, diminta string) bool {
	if strings.Contains(diminta, "..") {
		return false
	}
	// `Clean` di Windows mengubah pemisah menjadi `\`. Root harus dinormalisasi
	// dengan aturan yang sama, kalau tidak pemeriksaan "masih di dalam root"
	// di bawah selalu gagal dan seluruh berkas statis ditolak (permalink 404).
	root = filepath.Clean(root)
	bersih := filepath.Clean(filepath.Join(root, filepath.FromSlash(strings.TrimPrefix(diminta, "/"))))
	if bersih != root && !strings.HasPrefix(bersih, root+string(filepath.Separator)) {
		return false
	}
	if info, err := os.Stat(bersih); err == nil && info.IsDir() {
		bersih = filepath.Join(bersih, "index.html")
	}
	isi, err := os.ReadFile(bersih)
	if err != nil {
		return false
	}
	tipe := mime[strings.ToLower(filepath.Ext(bersih))]
	if tipe == "" {
		tipe = "application/octet-stream"
	}
	res.Header().Set("content-type", tipe)
	if strings.ToLower(filepath.Ext(bersih)) == ".html" {
		res.Header().Set("cache-control", "no-cache")
	} else {
		res.Header().Set("cache-control", "public, max-age=31536000, immutable")
	}
	res.WriteHeader(http.StatusOK)
	_, _ = res.Write(isi)
	return true
}

// Handler membangun http.Handler sidecar.
func Handler(o Opsi) http.Handler { return &handler{o: o} }

// Listen menjalankan server di port (0 = acak) dan mengembalikan port nyata.
func Listen(penangan http.Handler, port int, host string) (*http.Server, int, error) {
	peladen := &http.Server{Handler: penangan}
	pendengar, err := net.Listen("tcp", net.JoinHostPort(host, fmt.Sprint(port)))
	if err != nil {
		return nil, 0, err
	}
	portNyata := pendengar.Addr().(*net.TCPAddr).Port
	go func() {
		if err := peladen.Serve(pendengar); err != nil && !errors.Is(err, http.ErrServerClosed) {
			fmt.Printf("server berhenti: %v\n", err)
		}
	}()
	return peladen, portNyata, nil
}

func aturCors(res http.ResponseWriter) {
	res.Header().Set("access-control-allow-origin", "*")
	res.Header().Set("access-control-allow-headers", "content-type")
	res.Header().Set("access-control-allow-methods", "GET, POST, OPTIONS")
}

func tulisJson(res http.ResponseWriter, status int, isi interface{}) {
	aturCors(res)
	res.Header().Set("content-type", "application/json; charset=utf-8")
	res.Header().Set("cache-control", "no-store")
	res.WriteHeader(status)
	_ = json.NewEncoder(res).Encode(isi)
}
