// Package inference memuat antarmuka provider LLM dan dua implementasinya:
// OpenAI-compatible (llama-server / Ollama) dan stub untuk uji tanpa model.
//
// Ini adalah port dari `packages/provider-inference` +
// `packages/server-runtime/src/providers.ts`.
package inference

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"
)

// Message adalah satu pesan percakapan.
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// GenerateOptions adalah opsi pembangkitan yang dikirim ke provider.
type GenerateOptions struct {
	MaxTokens   int
	Temperature float64
	Deadline    time.Time
}

// Chunk adalah satu potongan hasil aliran; Err menandai akhir karena galat.
type Chunk struct {
	Text string
	Err  error
}

// Provider adalah antarmuka otak percakapan.
type Provider interface {
	// ID menandai provider untuk log dan header.
	ID() string
	// Available memeriksa kesiapan endpoint.
	Available(ctx context.Context) (bool, string)
	// Stream mengirim permintaan dan mengalirkan potongan teks.
	Stream(ctx context.Context, messages []Message, opts GenerateOptions) <-chan Chunk
	// Dispose melepaskan sumber daya provider.
	Dispose() error
}

// ───────────────────────── OpenAI-compatible ─────────────────────────

// OpenAiCompatibleProvider bicara dengan llama-server atau Ollama.
type OpenAiCompatibleProvider struct {
	id      string // 'llama-server' | 'ollama'
	baseUrl string
	model   string
	client  *http.Client
}

// NewOpenAi membuat provider OpenAI-compatible.
func NewOpenAi(id, baseUrl, model string) *OpenAiCompatibleProvider {
	return &OpenAiCompatibleProvider{
		id:      id,
		baseUrl: strings.TrimRight(baseUrl, "/"),
		model:   model,
		client:  &http.Client{},
	}
}

// ID mengembalikan penanda provider.
func (p *OpenAiCompatibleProvider) ID() string { return p.id }

// Available memeriksa endpoint kesehatan provider.
func (p *OpenAiCompatibleProvider) Available(ctx context.Context) (bool, string) {
	path := "/health"
	if p.id == "ollama" {
		path = "/api/tags"
	}
	ctx, cancel := context.WithTimeout(ctx, 1500*time.Millisecond)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, p.baseUrl+path, nil)
	if err != nil {
		return false, err.Error()
	}
	resp, err := p.client.Do(req)
	if err != nil {
		return false, err.Error()
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusOK {
		return true, "siap"
	}
	return false, "HTTP " + resp.Status
}

// Dispose tidak melakukan apa pun untuk provider jaringan.
func (p *OpenAiCompatibleProvider) Dispose() error { return nil }

type permintaanChat struct {
	Model       string    `json:"model"`
	Messages    []Message `json:"messages"`
	Stream      bool      `json:"stream"`
	MaxTokens   *int      `json:"max_tokens,omitempty"`
	Temperature *float64  `json:"temperature,omitempty"`
	Options     *struct {
		Temperature *float64 `json:"temperature,omitempty"`
	} `json:"options,omitempty"`
}

type deltaChunk struct {
	Choices []struct {
		Delta struct {
			Content string `json:"content"`
		} `json:"delta"`
	} `json:"choices"`
	Message *struct {
		Content string `json:"content"`
	} `json:"message"`
}

// pesanError mengekstrak pesan galat dari body respons yang tidak sukses.
func pesanError(body []byte) string {
	var parsed struct {
		Error interface{} `json:"error"`
	}
	if err := json.Unmarshal(body, &parsed); err == nil && parsed.Error != nil {
		switch v := parsed.Error.(type) {
		case string:
			return v
		case map[string]interface{}:
			if m, ok := v["message"]; ok {
				return strings.TrimSpace(string(mustJSON(m)))
			}
		}
	}
	return "respons inferensi tidak valid"
}

func mustJSON(v interface{}) []byte {
	b, _ := json.Marshal(v)
	return b
}

// Stream mengalirkan balasan dari endpoint chat.
func (p *OpenAiCompatibleProvider) Stream(ctx context.Context, messages []Message, opts GenerateOptions) <-chan Chunk {
	hasil := make(chan Chunk)
	go func() {
		defer close(hasil)
		ollama := p.id == "ollama"
		path := "/v1/chat/completions"
		if ollama {
			path = "/api/chat"
		}
		var body permintaanChat
		if ollama {
			body = permintaanChat{Model: p.model, Messages: messages, Stream: true,
				Options: &struct {
					Temperature *float64 `json:"temperature,omitempty"`
				}{Temperature: &opts.Temperature}}
		} else {
			body = permintaanChat{Model: p.model, Messages: messages, Stream: true,
				MaxTokens: &opts.MaxTokens, Temperature: &opts.Temperature}
		}
		encoded, err := json.Marshal(body)
		if err != nil {
			hasil <- Chunk{Err: err}
			return
		}
		req, err := http.NewRequestWithContext(ctx, http.MethodPost, p.baseUrl+path, strings.NewReader(string(encoded)))
		if err != nil {
			hasil <- Chunk{Err: err}
			return
		}
		req.Header.Set("content-type", "application/json")
		resp, err := p.client.Do(req)
		if err != nil {
			hasil <- Chunk{Err: err}
			return
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			potongan := make([]byte, 0, 4096)
			buffer := make([]byte, 4096)
			for {
				n, err := resp.Body.Read(buffer)
				potongan = append(potongan, buffer[:n]...)
				if err != nil || len(potongan) > 64*1024 {
					break
				}
			}
			hasil <- Chunk{Err: errors.New(p.id + " HTTP " + resp.Status + ": " + pesanError(potongan))}
			return
		}
		pemindai := bufio.NewScanner(resp.Body)
		pemindai.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
		for pemindai.Scan() {
			baris := strings.TrimSpace(pemindai.Text())
			if baris == "" {
				continue
			}
			payload := baris
			if !ollama {
				payload = strings.TrimPrefix(baris, "data:")
				payload = strings.TrimSpace(payload)
			}
			if payload == "[DONE]" {
				return
			}
			var data deltaChunk
			if err := json.Unmarshal([]byte(payload), &data); err != nil {
				continue
			}
			isi := ""
			if ollama {
				if data.Message != nil {
					isi = data.Message.Content
				}
			} else if len(data.Choices) > 0 {
				isi = data.Choices[0].Delta.Content
			}
			if isi == "" {
				continue
			}
			select {
			case <-ctx.Done():
				return
			case hasil <- Chunk{Text: isi}:
			}
		}
	}()
	return hasil
}

// ───────────────────────── stub ─────────────────────────

// StubProvider mengembalikan balasan tetap untuk menguji rantai tanpa model.
type StubProvider struct{}

// ID mengembalikan penanda provider.
func (StubProvider) ID() string { return "llama-server" }

// Available selalu siap.
func (StubProvider) Available(context.Context) (bool, string) { return true, "stub" }

// Dispose tidak melakukan apa pun.
func (StubProvider) Dispose() error { return nil }

// Stream mengembalikan potongan tetap.
func (StubProvider) Stream(ctx context.Context, _ []Message, _ GenerateOptions) <-chan Chunk {
	hasil := make(chan Chunk)
	go func() {
		defer close(hasil)
		for _, potongan := range []string{"[senyum] ", "Sistem inti sudah hidup, ", "Master."} {
			select {
			case <-ctx.Done():
				return
			case hasil <- Chunk{Text: potongan}:
			}
		}
	}()
	return hasil
}
