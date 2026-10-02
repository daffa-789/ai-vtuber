package config

import (
	"os"
	"path/filepath"
)

// CariAkarRepo menaiki direktori sampai menemukan manifest project (penanda
// monorepo). Padanan `cariAkarRepo()` di `paths.ts`, yang menggantikan
// `Path(__file__).parent.parent` yang rapuh terhadap posisi berkas.
func CariAkarRepo(dari string) string {
	dir := dari
	if info, err := os.Stat(dir); err != nil || !info.IsDir() {
		dir = filepath.Dir(dir)
	}
	for i := 0; i < 12; i++ {
		if _, err := os.Stat(filepath.Join(dir, "package.json")); err == nil {
			return dir
		}
		if _, err := os.Stat(filepath.Join(dir, ".git")); err == nil {
			return dir
		}
		naik := filepath.Dir(dir)
		if naik == dir {
			break
		}
		dir = naik
	}
	if cwd, err := os.Getwd(); err == nil {
		return cwd
	}
	return dari
}

// TemukanPersona adalah padanan `_temukan_persona()`: kandidat pertama yang ada,
// atau kandidat utama bila tidak ada yang ada.
func TemukanPersona(akar string) string {
	kandidat := []string{
		filepath.Join(akar, "silver_wolf_memory", "persona.md"),
		filepath.Join(akar, "silver wolf memory", "persona.md"),
		filepath.Join(akar, "memori-waifu", "persona.md"),
		filepath.Join(akar, "persona.md"),
	}
	for _, p := range kandidat {
		if info, err := os.Stat(p); err == nil && !info.IsDir() {
			return p
		}
	}
	return filepath.Join(akar, "silver_wolf_memory", "persona.md")
}

// BacaEnvAkar membaca `.env` di akar; kosong bila tidak ada.
func BacaEnvAkar(akar string) map[string]string {
	isi, err := os.ReadFile(filepath.Join(akar, ".env"))
	if err != nil {
		return map[string]string{}
	}
	return BacaEnv(string(isi))
}

// DariAkar adalah resolusi jalur relatif-akar (padanan `AKAR / "..."`).
func DariAkar(akar string, bagian ...string) string {
	return filepath.Join(append([]string{akar}, bagian...)...)
}
