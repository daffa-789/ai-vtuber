// Package agent mengorkestrasi percakapan: menyusun prompt, mengalirkan
// balasan dari provider, lalu menyimpan mood dan riwayat ke vault.
//
// Ini adalah port dari `packages/core-agent/src/index.ts`.
package agent

import (
	"context"
	"log"
	"regexp"
	"strings"

	"github.com/daffa-789/ai-vtuber/sidecar/internal/character"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/inference"
)

// Memory adalah isi vault yang ikut ke prompt.
type Memory struct {
	Fakta []string
	Mood  *character.Mood
}

// Agent adalah otak percakapan karakter.
type Agent struct {
	provider inference.Provider
	persona  string
	vault    *character.CharacterVault
	lokal    bool
	onError  func(error)
}

// Options adalah opsi pembuatan Agent.
type Options struct {
	Provider    inference.Provider
	Persona     string
	Vault       *character.CharacterVault
	LocalPrompt bool
	OnError     func(error)
}

// New membuat Agent.
func New(o Options) *Agent {
	// Prompt lokal (kontrak tag emosi) dipakai semua provider kecuali Ollama,
	// yang diarahkan ke persona gaya Ollama.
	lokal := o.LocalPrompt
	if o.Provider != nil && o.Provider.ID() == "ollama" {
		lokal = false
	}
	onError := o.OnError
	if onError == nil {
		onError = func(err error) { log.Printf("memori: %v", err) }
	}
	return &Agent{provider: o.Provider, persona: o.Persona, vault: o.Vault, lokal: lokal, onError: onError}
}

// LocalPrompt melaporkan apakah prompt memakai kontrak tag emosi lokal.
func (a *Agent) LocalPrompt() bool { return a.lokal }

// Memory memuat fakta dan mood dari vault; kosong bila vault tidak ada.
func (a *Agent) Memory() Memory {
	if a.vault == nil || !a.vault.Available() {
		return Memory{}
	}
	fakta, err := a.vault.BacaFakta()
	if err != nil {
		a.onError(err)
		return Memory{}
	}
	mood, err := a.vault.BacaMood()
	if err != nil {
		a.onError(err)
	}
	return Memory{Fakta: fakta, Mood: mood}
}

// Chat mengalirkan balasan karakter untuk satu riwayat percakapan.
//
// Balasan yang rampung disimpan ke vault (mood + riwayat harian). Penyimpanan
// tidak pernah menggagalkan aliran ke klien — cukup dicatat lewat OnError.
func (a *Agent) Chat(ctx context.Context, riwayat []inference.Message, opts inference.GenerateOptions) <-chan inference.Chunk {
	hasil := make(chan inference.Chunk)
	memory := a.Memory()
	pesan := make([]inference.Message, 0, len(riwayat)+1)
	pesan = append(pesan, inference.Message{
		Role:    "system",
		Content: character.GabungSystem(a.persona, memory.Fakta, memory.Mood, a.lokal),
	})
	for _, m := range riwayat {
		if m.Role != "system" {
			pesan = append(pesan, m)
		}
	}
	sumber := a.provider.Stream(ctx, pesan, opts)
	go func() {
		defer close(hasil)
		var jawaban strings.Builder
		for potongan := range sumber {
			if potongan.Err != nil {
				hasil <- potongan
				return
			}
			jawaban.WriteString(potongan.Text)
			select {
			case <-ctx.Done():
				return
			case hasil <- potongan:
			}
		}
		if jawaban.Len() > 0 {
			if err := a.persist(riwayat, jawaban.String(), memory); err != nil {
				a.onError(err)
			}
		}
	}()
	return hasil
}

var spasiGanda = regexp.MustCompile(`\s+`)

// persist menyimpan mood dan satu baris riwayat percakapan.
func (a *Agent) persist(riwayat []inference.Message, jawaban string, memory Memory) error {
	if a.vault == nil || !a.vault.Available() {
		return nil
	}
	mood := character.PerbaruiMood(memory.Mood, character.BacaTagAwal(jawaban))
	if err := a.vault.SimpanMood(mood); err != nil {
		return err
	}
	ucapan := ""
	for i := len(riwayat) - 1; i >= 0; i-- {
		if riwayat[i].Role == "user" {
			ucapan = riwayat[i].Content
			break
		}
	}
	ringkas := func(s string) string {
		padat := strings.TrimSpace(spasiGanda.ReplaceAllString(s, " "))
		if len(padat) > 240 {
			return padat[:240]
		}
		return padat
	}
	return a.vault.CatatHari("Master: " + ringkas(ucapan) + " | Silver Wolf: " + ringkas(jawaban))
}
