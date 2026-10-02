package agent

import (
	"context"
	"strings"
	"testing"

	"github.com/daffa-789/ai-vtuber/sidecar/internal/character"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/inference"
)

func TestChatMengalirkanDanMenyimpan(t *testing.T) {
	lumbung := character.NewVault(t.TempDir())
	otak := New(Options{
		Provider:    inference.StubProvider{},
		Persona:     "Kamu Silver Wolf.",
		Vault:       lumbung,
		LocalPrompt: true,
		OnError:     func(err error) { t.Errorf("galat tak terduga: %v", err) },
	})
	var kumpulan strings.Builder
	for potongan := range otak.Chat(context.Background(),
		[]inference.Message{{Role: "user", Content: "halo"}}, inference.GenerateOptions{}) {
		if potongan.Err != nil {
			t.Fatalf("aliran gagal: %v", potongan.Err)
		}
		kumpulan.WriteString(potongan.Text)
	}
	if kumpulan.String() != "[senyum] Sistem inti sudah hidup, Master." {
		t.Errorf("balasan = %q", kumpulan.String())
	}
	// Balasan yang rampung harus meninggalkan jejak mood dan riwayat.
	mood, err := lumbung.BacaMood()
	if err != nil || mood == nil {
		t.Fatalf("mood tidak tersimpan: %v", mood)
	}
	if mood.Pertukaran != 1 {
		t.Errorf("Pertukaran = %d, ingin 1", mood.Pertukaran)
	}
	// Tag [senyum] menaikkan valensi dari mood awal 0.2 (0.2*0.8 + 0.25*0.5).
	if mood.Valensi <= 0.2 {
		t.Errorf("Valensi = %v, ingin naik dari mood awal 0.2 berkat tag senyum", mood.Valensi)
	}
}

func TestChatTanpaVault(t *testing.T) {
	otak := New(Options{Provider: inference.StubProvider{}, Persona: "P", LocalPrompt: true})
	if !otak.LocalPrompt() {
		t.Error("prompt lokal harus aktif untuk provider selain Ollama")
	}
	var jumlah int
	for potongan := range otak.Chat(context.Background(), nil, inference.GenerateOptions{}) {
		if potongan.Err != nil {
			t.Fatalf("aliran gagal: %v", potongan.Err)
		}
		jumlah++
	}
	if jumlah != 3 {
		t.Errorf("potongan = %d, ingin 3", jumlah)
	}
}

func TestOllamaTanpaPromptLokal(t *testing.T) {
	otak := New(Options{
		Provider:    inference.NewOpenAi("ollama", "http://127.0.0.1:1", "x"),
		Persona:     "P",
		LocalPrompt: true,
	})
	if otak.LocalPrompt() {
		t.Error("Ollama tidak boleh memakai kontrak tag emosi lokal")
	}
}
