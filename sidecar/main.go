// Command silverwolf-sidecar adalah sidecar desktop Silver Wolf.
//
// Ia menggantikan sidecar Node (`apps/server` + `packages/server-runtime`):
// membaca `.env`, menjalankan llama-server bila perlu, menyusun prompt
// karakter, lalu menyajikan `/api/health` dan `/api/chat` (aliran teks) beserta
// berkas statis renderer dan model besar.
//
// Pemakaian dari Electron:
//
//	silverwolf-sidecar.exe -root <folder data> -port 0 -host 127.0.0.1 \
//	    -static <folder renderer> -assets <folder assets> -vault <folder memori>
//
// Port nyata dicetak ke stdout sebagai baris `port=<angka>` supaya Electron
// tidak perlu menebak atau memindai log.
package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/daffa-789/ai-vtuber/sidecar/internal/agent"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/character"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/config"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/inference"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/llama"
	"github.com/daffa-789/ai-vtuber/sidecar/internal/server"
)

const personaCadangan = "Kamu adalah Silver Wolf, hacker Punklorde dari Stellaron Hunters. " +
	"Kamu memanggil pengguna Master, bicara santai, ringkas, dan tidak memakai emoji."

type runtime struct {
	peladen *http.Server
	port    int
	llama   *llama.Process
	agent   *agent.Agent
}

func main() {
	akar := flag.String("root", "", "akar folder data (berisi .env, model/, assets/, silver_wolf_memory/)")
	port := flag.Int("port", -1, "port dengar; 0 = pilih port acak, -1 = ikuti .env")
	host := flag.String("host", "127.0.0.1", "antarmuka dengar")
	staticRoot := flag.String("static", "", "folder hasil build renderer (kosong saat dev Vite)")
	assetRoot := flag.String("assets", "", "folder model besar yang disajikan di /assets/ dan /models/")
	vaultRoot := flag.String("vault", "", "folder memori karakter (default <root>/silver_wolf_memory)")
	flag.Parse()

	if *akar == "" {
		if cwd, err := os.Getwd(); err == nil {
			*akar = config.CariAkarRepo(cwd)
		}
	}
	akarMutlak, err := filepath.Abs(*akar)
	if err != nil {
		fmt.Fprintf(os.Stderr, "akar tidak valid: %v\n", err)
		os.Exit(1)
	}

	env := config.BuatEnvSource(akarMutlak)
	konfig := config.BacaKonfig(&env, akarMutlak)
	if *port >= 0 {
		konfig.Port = *port
	}
	if *vaultRoot == "" {
		*vaultRoot = filepath.Join(akarMutlak, "silver_wolf_memory")
	}
	if *assetRoot == "" {
		*assetRoot = filepath.Join(akarMutlak, "assets")
	}

	jalan, err := jalankan(konfig, *host, *staticRoot, *assetRoot, *vaultRoot)
	if err != nil {
		fmt.Fprintf(os.Stderr, "sidecar gagal mulai: %v\n", err)
		os.Exit(1)
	}
	defer jalan.tutup()

	// Baris ini dibaca Electron untuk mengetahui port yang sebenarnya dipakai.
	fmt.Printf("port=%d\n", jalan.port)
	tungguSinyal()
}

func jalankan(konfig *config.Konfig, host, staticRoot, assetRoot, vaultRoot string) (*runtime, error) {
	persona := personaCadangan
	if isi, err := character.BacaPersona(konfig.AKarPersona); err == nil {
		persona = isi
	} else {
		fmt.Fprintf(os.Stderr, "! %v; memakai persona cadangan minimal\n", err)
	}
	lumbung := character.NewVault(vaultRoot)

	var provider inference.Provider
	var proses *llama.Process
	var namaModel string
	switch {
	case konfig.Stub:
		provider = inference.StubProvider{}
		namaModel = "stub"
	case konfig.LlmProvider == "ollama":
		provider = inference.NewOpenAi("ollama", konfig.OllamaUrl, konfig.OllamaModel)
		namaModel = "ollama/" + konfig.OllamaModel
	default:
		// Port acak mencegah tabrakan dengan llama-server yang sudah berjalan.
		portInferensi := 18788
		if konfig.Port != 0 {
			portInferensi = konfig.Port + 1
		}
		proses = llama.NewProcess(konfig, portInferensi)
		if ok, alasan := proses.Start(context.Background()); !ok {
			fmt.Fprintf(os.Stderr, "! inferensi lokal belum siap: %s\n", alasan)
		}
		model, _ := llama.CariModel(konfig, func(p string) { fmt.Fprintln(os.Stderr, p) })
		alias := llama.AliasModel(konfig, model)
		provider = inference.NewOpenAi("llama-server", fmt.Sprintf("http://127.0.0.1:%d", portInferensi), alias)
		awalan := "local"
		if konfig.LlmProvider == "vulkan" {
			awalan = "vulkan"
		}
		namaModel = awalan + "/" + alias
	}

	otak := agent.New(agent.Options{
		Provider:    provider,
		Persona:     persona,
		Vault:       lumbung,
		LocalPrompt: konfig.LlmProvider != "ollama",
		OnError:     func(err error) { fmt.Fprintf(os.Stderr, "memori: %v\n", err) },
	})
	peladen, portDengar, err := server.Listen(server.Handler(server.Opsi{
		Konfig:     konfig,
		Agent:      otak,
		Provider:   provider,
		Vault:      lumbung,
		ModelName:  namaModel,
		StaticRoot: staticRoot,
		AssetRoot:  assetRoot,
	}), konfig.Port, host)
	if err != nil {
		if proses != nil {
			proses.Stop()
		}
		return nil, err
	}
	fmt.Printf("Silver Wolf sidecar Go siap di http://%s:%d\n", host, portDengar)
	fmt.Printf("  model: %s · memori: %s\n", namaModel, namaMemori(lumbung))
	for _, w := range konfig.Warnings {
		fmt.Fprintf(os.Stderr, "  ! %s\n", w)
	}
	return &runtime{peladen: peladen, port: portDengar, llama: proses, agent: otak}, nil
}

func namaMemori(lumbung *character.CharacterVault) string {
	if lumbung.Available() {
		return "siap"
	}
	return lumbung.UnavailableReason()
}

func (r *runtime) tutup() {
	ctx, batal := context.WithTimeout(context.Background(), 3*time.Second)
	defer batal()
	if r.peladen != nil {
		_ = r.peladen.Shutdown(ctx)
	}
	if r.llama != nil {
		r.llama.Stop()
	}
}

func tungguSinyal() {
	sinyal := make(chan os.Signal, 1)
	signal.Notify(sinyal, os.Interrupt, syscall.SIGTERM)
	<-sinyal
}
