package llama

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/daffa-789/ai-vtuber/sidecar/internal/config"
)

func konfigUji(akar string, jalurModel string) *config.Konfig {
	env := &config.EnvSource{File: map[string]string{}, Environ: map[string]string{}}
	k := config.BacaKonfig(env, akar)
	if jalurModel != "" {
		k.LocalModelPath = jalurModel
	}
	return k
}

func TestCariModelEksplisitMenang(t *testing.T) {
	akar := t.TempDir()
	utama := filepath.Join(akar, "model", "utama.gguf")
	kadang := filepath.Join(akar, "model", "kadang.gguf")
	for _, p := range []string{utama, kadang} {
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte("x"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	k := konfigUji(akar, "model/utama.gguf")
	dapat, ok := CariModel(k, nil)
	if !ok || dapat != utama {
		t.Errorf("CariModel = %q, %v; ingin %q", dapat, ok, utama)
	}
	// Tanpa penunjuk eksplisit: pilihan deterministik (urut abjad) + peringatan.
	k2 := konfigUji(akar, "")
	peringatan := []string{}
	dapat2, ok2 := CariModel(k2, func(p string) { peringatan = append(peringatan, p) })
	if !ok2 {
		t.Fatal("model harus ditemukan lewat penelusuran folder")
	}
	if filepath.Base(dapat2) != "kadang.gguf" {
		t.Errorf("pilihan deterministik = %q, ingin kadang.gguf", filepath.Base(dapat2))
	}
	if len(peringatan) != 1 {
		t.Errorf("harus ada tepat satu peringatan soal banyak model, dapat %v", peringatan)
	}
}

func TestCariModelKosong(t *testing.T) {
	k := konfigUji(t.TempDir(), "")
	if dapat, ok := CariModel(k, nil); ok || dapat != "" {
		t.Errorf("CariModel tanpa GGUF = %q, %v; ingin kosong", dapat, ok)
	}
}

func TestDaftarModelTerurut(t *testing.T) {
	akar := t.TempDir()
	for _, nama := range []string{"c.gguf", "a.gguf", "b.gguf"} {
		p := filepath.Join(akar, "model", nama)
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte("x"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	dapat := DaftarModel(konfigUji(akar, ""))
	if len(dapat) != 3 {
		t.Fatalf("jumlah = %d, ingin 3", len(dapat))
	}
	for i, harap := range []string{"a.gguf", "b.gguf", "c.gguf"} {
		if filepath.Base(dapat[i]) != harap {
			t.Errorf("urutan[%d] = %q, ingin %q", i, filepath.Base(dapat[i]), harap)
		}
	}
}

func TestAliasModel(t *testing.T) {
	akar := t.TempDir()
	k := konfigUji(akar, "")
	if dapat := AliasModel(k, filepath.Join(akar, "model", "MiniCPM5-2B-Q4_K_M.gguf")); dapat != "MiniCPM5-2B-Q4_K_M" {
		t.Errorf("AliasModel = %q, ingin MiniCPM5-2B-Q4_K_M", dapat)
	}
	// Alias eksplisit menang atas nama berkas.
	k.LocalModelAlias = "NamaSendiri"
	if dapat := AliasModel(k, filepath.Join(akar, "model", "x.gguf")); dapat != "NamaSendiri" {
		t.Errorf("AliasModel eksplisit = %q, ingin NamaSendiri", dapat)
	}
	// Tanpa model sama sekali: jangan panik, pakai penanda generik.
	k2 := konfigUji(t.TempDir(), "")
	k2.LocalModelAlias = ""
	if dapat := AliasModel(k2, ""); dapat != "gguf" {
		t.Errorf("AliasModel tanpa model = %q, ingin gguf", dapat)
	}
}

func TestCariLlamaServer(t *testing.T) {
	akar := t.TempDir()
	if _, ok := CariLlamaServer(konfigUji(akar, "")); ok {
		t.Error("folder kosong tidak boleh menghasilkan binary")
	}
	// Binary ditemukan meski tersimpan beberapa lapis di dalam folder.
	dalam := filepath.Join(akar, "bin", "llama", "build", "llama-server.exe")
	if err := os.MkdirAll(filepath.Dir(dalam), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(dalam, []byte("x"), 0o755); err != nil {
		t.Fatal(err)
	}
	k := konfigUji(akar, "")
	k.LlamaServer = "bin/llama"
	dapat, ok := CariLlamaServer(k)
	if !ok || dapat != dalam {
		t.Errorf("CariLlamaServer = %q, %v; ingin %q", dapat, ok, dalam)
	}
}

func TestStartTanpaBinary(t *testing.T) {
	k := konfigUji(t.TempDir(), "")
	p := NewProcess(k, 18788)
	ok, alasan := p.Start(context.Background())
	if ok {
		t.Fatal("tanpa binary llama-server, Start harus gagal")
	}
	if !strings.Contains(alasan, "llama-server tidak ditemukan") {
		t.Errorf("alasan = %q, ingin menyebut llama-server tidak ditemukan", alasan)
	}
}
