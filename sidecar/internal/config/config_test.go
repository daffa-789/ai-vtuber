package config

import (
	"path/filepath"
	"testing"
)

func TestPotongKomentar(t *testing.T) {
	kasus := []struct {
		masuk      string
		harap      string
		keterangan string
	}{
		{`99  # semua lapis`, "99", "komentar setelah spasi dibuang"},
		{`#fff`, "#fff", "# di awal bukan komentar"},
		{`"isi # belum"`, "isi # belum", "nilai berkutip dipotong di kutip penutup"},
		{`'satu'`, "satu", "kutip tunggal dibuang"},
		{`key5=1 key3=0 # catatan`, "key5=1 key3=0", "resep param tetap utuh"},
		{`  spasi  `, "spasi", "spasi pinggir dibuang"},
	}
	for _, k := range kasus {
		if dapat := PotongKomentar(k.masuk); dapat != k.harap {
			t.Errorf("%s: PotongKomentar(%q) = %q, ingin %q", k.keterangan, k.masuk, dapat, k.harap)
		}
	}
}

func TestBacaEnv(t *testing.T) {
	isi := "# komentar\nVTUBER_PORT=8787\nVTUBER_STUB=ya  # aktif\n\nVTUBER_RVC_FOLDER=aset/suara/rvc\nbaris-tanpa-sama\n=tanpa-kunci\n"
	dapat := BacaEnv(isi)
	if dapat["VTUBER_PORT"] != "8787" {
		t.Errorf("VTUBER_PORT = %q, ingin 8787", dapat["VTUBER_PORT"])
	}
	if dapat["VTUBER_STUB"] != "ya" {
		t.Errorf("VTUBER_STUB = %q, ingin ya (komentar harus terbuang)", dapat["VTUBER_STUB"])
	}
	if _, ada := dapat["baris-tanpa-sama"]; ada {
		t.Error("baris tanpa '=' tidak boleh masuk")
	}
	if _, ada := dapat[""]; ada {
		t.Error("kunci kosong tidak boleh masuk")
	}
}

func TestBersih(t *testing.T) {
	if dapat := Bersih(`"terkutip"`); dapat != "terkutip" {
		t.Errorf("Bersih = %q, ingin terkutip", dapat)
	}
	if dapat := Bersih("polos"); dapat != "polos" {
		t.Errorf("Bersih = %q, ingin polos", dapat)
	}
}

func TestKoerser(t *testing.T) {
	env := &EnvSource{File: map[string]string{
		"ANGKA":       "12",
		"ANGKA_RUSAK": "bukan",
		"FLOAT":       "0.5",
		"BOOL_YA":     "ya",
		"BOOL_TIDAK":  "tidak",
		"BOOL_RUSAK":  "mungkin",
		"DAFTAR":      "piper+rvc, piper ,,",
	}, Environ: map[string]string{"DARI_LINGKUNGAN": "nilai-env"}}

	if dapat := Angka(env, "ANGKA", 4); dapat != 12 {
		t.Errorf("Angka = %d, ingin 12", dapat)
	}
	if dapat := Angka(env, "ANGKA_RUSAK", 4); dapat != 4 {
		t.Errorf("Angka rusak = %d, ingin bawaan 4", dapat)
	}
	if dapat := AngkaFloat(env, "FLOAT", 1); dapat != 0.5 {
		t.Errorf("AngkaFloat = %v, ingin 0.5", dapat)
	}
	if dapat := Bool(env, "BOOL_YA", false); !dapat {
		t.Error("Bool 'ya' harus true")
	}
	if dapat := Bool(env, "BOOL_TIDAK", true); dapat {
		t.Error("Bool 'tidak' harus false")
	}
	if dapat := Bool(env, "BOOL_RUSAK", true); !dapat {
		t.Error("Bool rusak harus jatuh ke bawaan true")
	}
	if dapat := Daftar(env, "DAFTAR", "x"); len(dapat) != 2 || dapat[0] != "piper+rvc" || dapat[1] != "piper" {
		t.Errorf("Daftar = %v, ingin [piper+rvc piper]", dapat)
	}
	if dapat := Nilai(env, "DARI_LINGKUNGAN", "bawaan"); dapat != "nilai-env" {
		t.Errorf("Nilai = %q, ingin nilai-env (lingkungan menang)", dapat)
	}
	// Nilai yang gagal diparse HARUS tercatat, bukan hilang tanpa jejak.
	if len(env.Warnings) != 2 {
		t.Errorf("Warnings = %v, ingin 2 peringatan (angka rusak + bool rusak)", env.Warnings)
	}
}

func TestBacaKonfigBawaan(t *testing.T) {
	env := &EnvSource{File: map[string]string{}, Environ: map[string]string{}}
	k := BacaKonfig(env, "C:\\akar")
	if k.Port != 8787 {
		t.Errorf("Port = %d, ingin 8787", k.Port)
	}
	if k.Tampak != "pet" {
		t.Errorf("Tampak = %q, ingin pet", k.Tampak)
	}
	if k.PetSembunyi != "layar-penuh" {
		t.Errorf("PetSembunyi = %q, ingin layar-penuh", k.PetSembunyi)
	}
	if !k.PetTray {
		t.Error("PetTray harus true secara bawaan")
	}
	if k.PetHotkey != "ctrl+shift+s" {
		t.Errorf("PetHotkey = %q, ingin ctrl+shift+s", k.PetHotkey)
	}
	if k.LlmProvider != "local" {
		t.Errorf("LlmProvider = %q, ingin local", k.LlmProvider)
	}
	if k.LocalMinP != 0 {
		t.Errorf("LocalMinP = %v, ingin 0 (wajib untuk MiniCPM5)", k.LocalMinP)
	}
	if k.LocalReasoning != "off" {
		t.Errorf("LocalReasoning = %q, ingin off", k.LocalReasoning)
	}
	// VulkanCtx 0 berarti ikut konteks model lokal.
	if k.VulkanCtx != k.LocalModelCtx {
		t.Errorf("VulkanCtx = %d, ingin mengikuti LocalModelCtx %d", k.VulkanCtx, k.LocalModelCtx)
	}
	if k.MaksPesan != 24 || k.MaksKarakter != 4000 || k.MaksBody != 64*1024 {
		t.Errorf("batas = %d/%d/%d, ingin 24/4000/65536", k.MaksPesan, k.MaksKarakter, k.MaksBody)
	}
}

func TestBacaKonfigPenjepitan(t *testing.T) {
	env := &EnvSource{File: map[string]string{
		"VTUBER_TAMPAK":       "aneh",
		"VTUBER_PET_SEMBUNYI": "maksimal",
		"VTUBER_LLM_PROVIDER": "VULKAN",
		"VTUBER_VULKAN_CTX":   "4096",
		"VTUBER_PORT":         "9000",
	}, Environ: map[string]string{}}
	k := BacaKonfig(env, "C:\\akar")
	if k.Tampak != "pet" {
		t.Errorf("Tampak = %q, ingin pet (nilai asing dijepit)", k.Tampak)
	}
	if k.PetSembunyi != "maksimal" {
		t.Errorf("PetSembunyi = %q, ingin maksimal", k.PetSembunyi)
	}
	if k.LlmProvider != "vulkan" {
		t.Errorf("LlmProvider = %q, ingin vulkan (huruf besar dinormalkan)", k.LlmProvider)
	}
	if k.VulkanCtx != 4096 {
		t.Errorf("VulkanCtx = %d, ingin 4096", k.VulkanCtx)
	}
	if k.Port != 9000 {
		t.Errorf("Port = %d, ingin 9000", k.Port)
	}
}

func TestTemukanPersona(t *testing.T) {
	akar := t.TempDir()
	// Belum ada berkas apa pun: harus jatuh ke kandidat utama, bukan panik.
	harap := filepath.Join(akar, "silver_wolf_memory", "persona.md")
	if dapat := TemukanPersona(akar); dapat != harap {
		t.Errorf("TemukanPersona = %q, ingin %q", dapat, harap)
	}
}
