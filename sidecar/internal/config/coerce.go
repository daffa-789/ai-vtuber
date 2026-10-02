package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

// EnvSource adalah sumber nilai konfigurasi: berkas `.env` ditimpa lingkungan
// proses. Padanan `EnvSource` di `coerce.ts`.
type EnvSource struct {
	// File adalah nilai dari `.env` (sudah dipotong komentarnya).
	File map[string]string
	// Environ adalah nilai dari lingkungan proses; menang atas berkas bila tidak kosong.
	Environ map[string]string
	// Warnings menampung peringatan parse; diisi oleh koerser di bawah.
	Warnings []string
}

// BuatEnvSource membangun EnvSource dari `.env` di akar + lingkungan proses.
func BuatEnvSource(akar string) EnvSource {
	return EnvSource{File: BacaEnvAkar(akar), Environ: Environ()}
}

// Environ menyalin lingkungan proses ke peta biasa.
func Environ() map[string]string {
	hasil := map[string]string{}
	for _, pasangan := range os.Environ() {
		if idx := strings.IndexByte(pasangan, '='); idx > 0 {
			hasil[pasangan[:idx]] = pasangan[idx+1:]
		}
	}
	return hasil
}

// Warn mencatat peringatan parse.
func (e *EnvSource) Warn(pesan string) { e.Warnings = append(e.Warnings, pesan) }

// Nilai adalah padanan `nilai(kunci, bawaan)`.
func Nilai(env *EnvSource, kunci string, bawaan string) string {
	if dariEnv, ok := env.Environ[kunci]; ok && strings.TrimSpace(dariEnv) != "" {
		return Bersih(dariEnv)
	}
	if v, ok := env.File[kunci]; ok {
		return v
	}
	return bawaan
}

// Angka adalah padanan `angka()`: gagal parse => bawaan + peringatan.
func Angka(env *EnvSource, kunci string, bawaan int) int {
	mentah := strings.TrimSpace(Nilai(env, kunci, strconv.Itoa(bawaan)))
	if mentah == "" {
		return bawaan
	}
	n, err := strconv.Atoi(mentah)
	if err != nil {
		env.Warn(fmt.Sprintf("%s=%q bukan bilangan bulat; dipakai bawaan %d", kunci, mentah, bawaan))
		return bawaan
	}
	return n
}

// AngkaFloat adalah padanan `angka_float()` untuk rasio (protect 0.33, length_scale 1.0).
func AngkaFloat(env *EnvSource, kunci string, bawaan float64) float64 {
	mentah := strings.TrimSpace(Nilai(env, kunci, strconv.FormatFloat(bawaan, 'f', -1, 64)))
	if mentah == "" {
		return bawaan
	}
	n, err := strconv.ParseFloat(mentah, 64)
	if err != nil {
		env.Warn(fmt.Sprintf("%s=%q bukan bilangan; dipakai bawaan %s", kunci, mentah,
			strconv.FormatFloat(bawaan, 'f', -1, 64)))
		return bawaan
	}
	return n
}

// Bool adalah padanan `bool_()`: true|1|ya|on dan false|0|tidak|off, selain itu bawaan.
func Bool(env *EnvSource, kunci string, bawaan bool) bool {
	mentah := strings.ToLower(strings.TrimSpace(Nilai(env, kunci, fmt.Sprint(bawaan))))
	switch mentah {
	case "true", "1", "ya", "on":
		return true
	case "false", "0", "tidak", "off":
		return false
	}
	env.Warn(fmt.Sprintf("%s=%q bukan boolean; dipakai bawaan %t", kunci, mentah, bawaan))
	return bawaan
}

// Daftar adalah padanan `daftar()`: pisah koma, buang yang kosong.
func Daftar(env *EnvSource, kunci string, bawaan string) []string {
	hasil := []string{}
	for _, bagian := range strings.Split(Nilai(env, kunci, bawaan), ",") {
		if s := strings.TrimSpace(bagian); s != "" {
			hasil = append(hasil, s)
		}
	}
	return hasil
}
