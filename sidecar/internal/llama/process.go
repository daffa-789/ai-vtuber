// Package llama mengelola proses `llama-server` dan pemilihan model GGUF.
// Ini adalah port dari `packages/server-runtime/src/llama-process.ts`.
package llama

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/daffa-789/ai-vtuber/sidecar/internal/config"
)

// cari menelusuri folder (dan berkas) sampai menemukan nama yang cocok.
func cari(root string, cocok func(string) bool, kedalaman int) (string, bool) {
	info, err := os.Stat(root)
	if err != nil {
		return "", false
	}
	if !info.IsDir() {
		return root, cocok(filepath.Base(root))
	}
	entri, err := os.ReadDir(root)
	if err != nil {
		return "", false
	}
	for _, item := range entri {
		path := filepath.Join(root, item.Name())
		if !item.IsDir() && cocok(item.Name()) {
			return path, true
		}
		if item.IsDir() && kedalaman > 0 {
			if ketemu, ok := cari(path, cocok, kedalaman-1); ok {
				return ketemu, true
			}
		}
	}
	return "", false
}

func cariSemua(root string, cocok func(string) bool, kedalaman int) []string {
	info, err := os.Stat(root)
	if err != nil || !info.IsDir() {
		return nil
	}
	entri, err := os.ReadDir(root)
	if err != nil {
		return nil
	}
	hasil := []string{}
	for _, item := range entri {
		path := filepath.Join(root, item.Name())
		if !item.IsDir() && cocok(item.Name()) {
			hasil = append(hasil, path)
		} else if item.IsDir() && kedalaman > 0 {
			hasil = append(hasil, cariSemua(path, cocok, kedalaman-1)...)
		}
	}
	return hasil
}

// DaftarModel mendaftar semua `.gguf` yang terlihat, terurut supaya hasilnya
// bisa diulang.
//
// Urutan `os.ReadDir` bergantung sistem berkas, jadi "yang pertama ketemu"
// bukan pilihan yang bisa dipertanggungjawabkan saat ada lebih dari satu model.
func DaftarModel(k *config.Konfig) []string {
	akar := []string{}
	if k.LocalModelPath != "" {
		eksplisit := filepath.Join(k.Akar, k.LocalModelPath)
		if info, err := os.Stat(eksplisit); err == nil && !info.IsDir() {
			akar = append(akar, eksplisit)
		}
	}
	for _, dir := range []string{"model", filepath.Join("assets", "llm")} {
		for _, f := range cariSemua(filepath.Join(k.Akar, dir), func(nama string) bool {
			return strings.EqualFold(filepath.Ext(nama), ".gguf")
		}, 2) {
			sudah := false
			for _, x := range akar {
				if x == f {
					sudah = true
					break
				}
			}
			if !sudah {
				akar = append(akar, f)
			}
		}
	}
	sort.Slice(akar, func(i, j int) bool {
		return strings.ToLower(filepath.Base(akar[i])) < strings.ToLower(filepath.Base(akar[j]))
	})
	return akar
}

// CariModel memilih berkas model.
//
// Kalau `VTUBER_LOCAL_MODEL_PATH` menunjuk berkas yang ada, itu yang menang —
// tidak ada tebakan. Kalau tidak, dan ada LEBIH DARI SATU `.gguf`, pilihannya
// tidak bisa ditebak dengan benar, jadi kita pilih satu secara deterministik
// lalu berteriak di log.
func CariModel(k *config.Konfig, log func(string)) (string, bool) {
	if k.LocalModelPath != "" {
		eksplisit := filepath.Join(k.Akar, k.LocalModelPath)
		if info, err := os.Stat(eksplisit); err == nil && !info.IsDir() {
			return eksplisit, true
		}
	}
	semua := DaftarModel(k)
	if len(semua) == 0 {
		return "", false
	}
	if len(semua) == 1 {
		return semua[0], true
	}
	if log != nil {
		kandidat := make([]string, 0, len(semua))
		for _, f := range semua {
			kandidat = append(kandidat, filepath.Base(f))
		}
		log(fmt.Sprintf("! %d model GGUF ditemukan dan VTUBER_LOCAL_MODEL_PATH tidak menunjuk berkas: "+
			"memilih %q. Setel VTUBER_LOCAL_MODEL_PATH agar tidak menebak. Kandidat: %s",
			len(semua), filepath.Base(semua[0]), strings.Join(kandidat, ", ")))
	}
	return semua[0], true
}

// AliasModel adalah nama model yang dikirim ke `/v1/chat/completions`.
//
// Dulu ini diisi path absolut berkas .gguf — llama.cpp kebetulan menolerannya,
// tapi rapuh dan bocor ke log. Sekarang turun dari nama berkas (tanpa ekstensi)
// kecuali `VTUBER_LOCAL_MODEL_ALIAS` diisi.
func AliasModel(k *config.Konfig, model string) string {
	if eksplisit := strings.TrimSpace(k.LocalModelAlias); eksplisit != "" {
		return eksplisit
	}
	if model == "" {
		model, _ = CariModel(k, nil)
	}
	if model == "" {
		return "gguf"
	}
	return strings.TrimSuffix(filepath.Base(model), filepath.Ext(model))
}

// CariLlamaServer menemukan binary llama-server di folder yang dikonfigurasi.
func CariLlamaServer(k *config.Konfig) (string, bool) {
	root := filepath.Join(k.Akar, k.LlamaServer)
	nama := "llama-server"
	if runtime.GOOS == "windows" {
		nama = "llama-server.exe"
	}
	return cari(root, func(n string) bool { return strings.EqualFold(n, nama) }, 3)
}

// ───────────────────────── proses ─────────────────────────

// penulisAwalan memberi awalan ke setiap baris yang ditulis proses anak,
// supaya log llama-server bisa dibedakan dari log sidecar.
type penulisAwalan struct {
	mu     sync.Mutex
	target io.Writer
	awalan string
	sisa   []byte
}

func (p *penulisAwalan) Write(data []byte) (int, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.sisa = append(p.sisa, data...)
	for {
		idx := -1
		for i, b := range p.sisa {
			if b == '\n' {
				idx = i
				break
			}
		}
		if idx < 0 {
			break
		}
		baris := p.sisa[:idx+1]
		p.sisa = p.sisa[idx+1:]
		if _, err := io.WriteString(p.target, p.awalan+string(baris)); err != nil {
			return len(data), err
		}
	}
	return len(data), nil
}

// Process mengelola satu proses llama-server.
type Process struct {
	config *config.Konfig
	Port   int
	cmd    *exec.Cmd
	beres  sync.WaitGroup
}

// NewProcess membuat pengelola proses untuk port tertentu.
func NewProcess(k *config.Konfig, port int) *Process {
	return &Process{config: k, Port: port}
}

// Start menjalankan llama-server dan menunggu sampai endpoint health menjawab.
func (p *Process) Start(ctx context.Context) (bool, string) {
	binary, ok := CariLlamaServer(p.config)
	if !ok {
		return false, fmt.Sprintf("llama-server tidak ditemukan di %s", p.config.LlamaServer)
	}
	model, ok := CariModel(p.config, func(pesan string) { fmt.Fprintln(os.Stderr, pesan) })
	if !ok {
		return false, "model GGUF tidak ditemukan"
	}
	vulkan := p.config.LlmProvider == "vulkan"
	ctxKonteks := p.config.LocalModelCtx
	ngl := 0
	if vulkan {
		ctxKonteks = p.config.VulkanCtx
		ngl = p.config.VulkanNgl
	}
	args := []string{
		"-m", model,
		"-a", AliasModel(p.config, model),
		"--host", "127.0.0.1",
		"--port", fmt.Sprint(p.Port),
		"-c", fmt.Sprint(ctxKonteks),
		"-t", fmt.Sprint(p.config.LocalModelThreads),
		"-ngl", fmt.Sprint(ngl),
	}
	if vulkan && p.config.VulkanFa {
		args = append(args, "--flash-attn", "on")
	}
	// Sampling jadi bawaan server karena klien hanya mengirim temperature+max_tokens.
	// min_p=0 itu wajib untuk MiniCPM5 (bawaan llama.cpp 0,05 => output mengulang),
	// dan -rea off mematikan mode berpikir yang akan mengawali balasan dengan <think>.
	args = append(args, "--jinja", "--min-p", fmt.Sprint(p.config.LocalMinP),
		"--top-p", fmt.Sprint(p.config.LocalTopP), "-rea", p.config.LocalReasoning)

	cmd := exec.Command(binary, args...)
	cmd.Dir = p.config.Akar
	cmd.Stdout = &penulisAwalan{target: os.Stdout, awalan: "[llama] "}
	cmd.Stderr = &penulisAwalan{target: os.Stderr, awalan: "[llama] "}
	sembunyikanJendela(cmd)
	if err := cmd.Start(); err != nil {
		return false, err.Error()
	}
	p.cmd = cmd
	alasan := "waktu tunggu llama-server habis"
	klien := &http.Client{Timeout: time.Second}
	for i := 0; i < 120; i++ {
		if cmd.ProcessState != nil {
			return false, fmt.Sprintf("llama-server berhenti (kode %d)", cmd.ProcessState.ExitCode())
		}
		req, err := http.NewRequestWithContext(ctx, http.MethodGet,
			fmt.Sprintf("http://127.0.0.1:%d/health", p.Port), nil)
		if err == nil {
			if resp, err := klien.Do(req); err == nil {
				status := resp.StatusCode
				resp.Body.Close()
				if status == http.StatusOK {
					return true, "siap"
				}
				alasan = fmt.Sprintf("health HTTP %d", status)
			}
		}
		select {
		case <-ctx.Done():
			p.Stop()
			return false, "dibatalkan"
		case <-time.After(250 * time.Millisecond):
		}
	}
	p.Stop()
	return false, alasan
}

// Stop menghentikan proses anak: SIGTERM, tunggu 1,5 detik, lalu paksa.
func (p *Process) Stop() {
	if p.cmd == nil || p.cmd.Process == nil {
		return
	}
	proc := p.cmd.Process
	p.cmd = nil
	if proc == nil {
		return
	}
	_ = proc.Signal(os.Interrupt)
	selesai := make(chan struct{})
	go func() {
		_, _ = proc.Wait()
		close(selesai)
	}()
	select {
	case <-selesai:
	case <-time.After(1500 * time.Millisecond):
		_ = proc.Kill()
	}
}
