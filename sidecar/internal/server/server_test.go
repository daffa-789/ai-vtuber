package server

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/daffa-789/ai-vtuber/sidecar/internal/agent"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/character"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/config"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/inference"
)

func opsiUji() Opsi {
	konfig := config.BacaKonfig(&config.EnvSource{
		File:    map[string]string{},
		Environ: map[string]string{"VTUBER_STUB": "ya"},
	}, "C:\\akar")
	lumbung := character.NewVault(os.TempDir())
	provider := inference.StubProvider{}
	otak := agent.New(agent.Options{Provider: provider, Persona: "PERSONA", Vault: lumbung, LocalPrompt: true})
	return Opsi{Konfig: konfig, Agent: otak, Provider: provider, Vault: lumbung, ModelName: "stub"}
}

func TestHealth(t *testing.T) {
	res := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	Handler(opsiUji()).ServeHTTP(res, req)
	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, ingin 200", res.Code)
	}
	var isi HealthResponse
	if err := json.Unmarshal(res.Body.Bytes(), &isi); err != nil {
		t.Fatalf("health bukan JSON: %v (%s)", err, res.Body.String())
	}
	if !isi.OK || isi.Model != "stub" {
		t.Errorf("health = %+v, ingin ok=true model=stub", isi)
	}
	if isi.Sisi != "go" {
		t.Errorf("sisi = %q, ingin go", isi.Sisi)
	}
	if res.Header().Get("access-control-allow-origin") != "*" {
		t.Error("header CORS harus ikut (renderer Electron memakai origin file/http)")
	}
}

func TestChatMengalirkanTeks(t *testing.T) {
	res := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/chat",
		strings.NewReader(`{"messages":[{"role":"user","content":"halo"}]}`))
	Handler(opsiUji()).ServeHTTP(res, req)
	if res.Code != http.StatusOK {
		t.Fatalf("status = %d, ingin 200 (%s)", res.Code, res.Body.String())
	}
	if dapat := res.Body.String(); dapat != "[senyum] Sistem inti sudah hidup, Master." {
		t.Errorf("isi aliran = %q", dapat)
	}
	if res.Header().Get("content-type") != "text/plain; charset=utf-8" {
		t.Errorf("content-type = %q, ingin text/plain", res.Header().Get("content-type"))
	}
}

func TestChatRiwayatKosong(t *testing.T) {
	res := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/chat", strings.NewReader(`{"messages":[]}`))
	Handler(opsiUji()).ServeHTTP(res, req)
	if res.Code != http.StatusBadRequest {
		t.Errorf("status = %d, ingin 400 untuk riwayat kosong", res.Code)
	}
}

func TestChatBodyRusak(t *testing.T) {
	res := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/api/chat", strings.NewReader(`bukan json`))
	Handler(opsiUji()).ServeHTTP(res, req)
	if res.Code != http.StatusBadRequest {
		t.Errorf("status = %d, ingin 400 untuk body rusak", res.Code)
	}
}

func TestChatMethodSalah(t *testing.T) {
	res := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/api/chat", nil)
	Handler(opsiUji()).ServeHTTP(res, req)
	if res.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, ingin 405 untuk GET /api/chat", res.Code)
	}
}

func TestRapikanRiwayat(t *testing.T) {
	mentah := []interface{}{
		map[string]interface{}{"role": "user", "content": "satu"},
		map[string]interface{}{"role": "model", "content": "dua"},
		map[string]interface{}{"role": "user", "content": "   "},
		map[string]interface{}{"role": "user", "parts": []interface{}{
			map[string]interface{}{"text": "tiga"}, map[string]interface{}{"text": "empat"},
		}},
		"bukan objek",
	}
	dapat := RapikanRiwayat(mentah, 24, 4000)
	if len(dapat) != 3 {
		t.Fatalf("jumlah pesan = %d, ingin 3", len(dapat))
	}
	if dapat[1].Role != "assistant" {
		t.Errorf("role 'model' harus dinormalisasi ke assistant, dapat %q", dapat[1].Role)
	}
	if dapat[2].Content != "tiga empat" {
		t.Errorf("parts harus digabung, dapat %q", dapat[2].Content)
	}
	// Riwayat yang kepanjangan dipotong dari yang terbaru.
	banyak := make([]interface{}, 0, 30)
	for i := 0; i < 30; i++ {
		banyak = append(banyak, map[string]interface{}{"role": "user", "content": "x"})
	}
	if dapat := RapikanRiwayat(banyak, 24, 4000); len(dapat) != 24 {
		t.Errorf("pesan dipotong = %d, ingin 24", len(dapat))
	}
	// Konten yang kepanjangan dipotong per pesan.
	panjang := []interface{}{map[string]interface{}{"role": "user", "content": strings.Repeat("a", 50)}}
	if dapat := RapikanRiwayat(panjang, 24, 10); len(dapat[0].Content) != 10 {
		t.Errorf("konten dipotong = %d, ingin 10", len(dapat[0].Content))
	}
	if dapat := RapikanRiwayat("bukan array", 24, 4000); len(dapat) != 0 {
		t.Error("masukan bukan array harus menghasilkan riwayat kosong")
	}
}

func TestSajiStatisMenolakPathLuar(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "index.html"), []byte("<h1>halo</h1>"), 0o644); err != nil {
		t.Fatal(err)
	}
	res := httptest.NewRecorder()
	if !sajiStatis(res, root, "/index.html") {
		t.Fatal("berkas yang ada harus tersaji")
	}
	if res.Body.String() != "<h1>halo</h1>" {
		t.Errorf("isi = %q", res.Body.String())
	}
	// Path berisi '..' tidak boleh lolos dari root.
	res2 := httptest.NewRecorder()
	if sajiStatis(res2, root, "/../rahasia.txt") {
		t.Error("path traversal harus ditolak")
	}
}

func TestStatisLewatHandler(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "app.js"), []byte("console.log(1)"), 0o644); err != nil {
		t.Fatal(err)
	}
	o := opsiUji()
	o.StaticRoot = root
	res := httptest.NewRecorder()
	Handler(o).ServeHTTP(res, httptest.NewRequest(http.MethodGet, "/app.js", nil))
	if res.Code != http.StatusOK || res.Body.String() != "console.log(1)" {
		t.Errorf("statis = %d %q", res.Code, res.Body.String())
	}
	// SPA fallback: rute yang tidak dikenal jatuh ke index.html.
	if err := os.WriteFile(filepath.Join(root, "index.html"), []byte("<html></html>"), 0o644); err != nil {
		t.Fatal(err)
	}
	res2 := httptest.NewRecorder()
	Handler(o).ServeHTTP(res2, httptest.NewRequest(http.MethodGet, "/halaman/aneh", nil))
	if res2.Code != http.StatusOK || res2.Body.String() != "<html></html>" {
		t.Errorf("fallback SPA = %d %q", res2.Code, res2.Body.String())
	}
}

func TestTidakDitemukan(t *testing.T) {
	res := httptest.NewRecorder()
	Handler(opsiUji()).ServeHTTP(res, httptest.NewRequest(http.MethodGet, "/tidak-ada", nil))
	if res.Code != http.StatusNotFound {
		t.Errorf("status = %d, ingin 404", res.Code)
	}
}

func TestOptions(t *testing.T) {
	res := httptest.NewRecorder()
	Handler(opsiUji()).ServeHTTP(res, httptest.NewRequest(http.MethodOptions, "/api/chat", nil))
	if res.Code != http.StatusNoContent {
		t.Errorf("status OPTIONS = %d, ingin 204", res.Code)
	}
}

func TestListenPortAcak(t *testing.T) {
	peladen, port, err := Listen(Handler(opsiUji()), 0, "127.0.0.1")
	if err != nil {
		t.Fatalf("Listen: %v", err)
	}
	defer peladen.Close()
	if port == 0 {
		t.Error("port acak harus terisi, bukan 0")
	}
}
