package character

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

var tautan = []string{"silverwolf-persona"}

func tanggal(waktu time.Time) string { return waktu.UTC().Format("2006-01-02") }

// CharacterVault adalah penyimpan memori karakter di folder markdown lokal.
// Padanan `CharacterVault` di `packages/core-character/src/vault.ts`.
type CharacterVault struct {
	Root string
}

// NewVault membuat vault di folder root.
func NewVault(root string) *CharacterVault { return &CharacterVault{Root: root} }

// Available melaporkan apakah folder vault ada.
func (v *CharacterVault) Available() bool {
	info, err := os.Stat(v.Root)
	return err == nil && info.IsDir()
}

// UnavailableReason adalah alasan teknis saat vault tidak tersedia.
func (v *CharacterVault) UnavailableReason() string {
	return fmt.Sprintf("folder %s tidak ada", v.Root)
}

func (v *CharacterVault) baca(nama string) (string, error) {
	isi, err := os.ReadFile(filepath.Join(v.Root, nama))
	if err != nil {
		if os.IsNotExist(err) {
			return "", nil
		}
		return "", err
	}
	return string(isi), nil
}

// tulis menulis berkas secara atomik (temp + rename) supaya berkas memori
// tidak pernah terbaca setengah jadi.
func (v *CharacterVault) tulis(nama string, isi string) error {
	path := filepath.Join(v.Root, nama)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	temp := fmt.Sprintf("%s.%d.%d.tmp", path, os.Getpid(), time.Now().UnixNano())
	if err := os.WriteFile(temp, []byte(isi), 0o644); err != nil {
		return err
	}
	return os.Rename(temp, path)
}

func kerangka(nama, judul, isi string, links []string) string {
	semua := make([]string, 0, len(tautan)+len(links))
	semua = append(semua, tautan...)
	semua = append(semua, links...)
	// buang duplikat dengan mempertahankan urutan
	lihat := map[string]bool{}
	unik := []string{}
	for _, x := range semua {
		if !lihat[x] {
			lihat[x] = true
			unik = append(unik, x)
		}
	}
	baris := []string{
		"---", "type: memory", "kind: karakter", "wilayah: waifu",
		fmt.Sprintf("name: %q", nama),
		fmt.Sprintf("description: %q", judul),
		`project: "Desktop AI VTUBER"`,
		fmt.Sprintf("updated: %q", tanggal(time.Now())),
		"tags:", `  - "memory/karakter"`, `  - "wilayah/waifu"`, `  - "project/Desktop AI VTUBER"`,
		"links:",
	}
	for _, x := range unik {
		baris = append(baris, fmt.Sprintf("  - \"[[%s]]\"", x))
	}
	baris = append(baris, "---", "", "# "+judul, "", strings.TrimSpace(isi), "")
	return strings.Join(baris, "\n")
}

// BacaFakta membaca daftar fakta yang tersimpan tentang Master.
func (v *CharacterVault) BacaFakta() ([]string, error) {
	teks, err := v.baca("Fakta.md")
	if err != nil {
		return nil, err
	}
	hasil := []string{}
	for _, baris := range strings.Split(teks, "\n") {
		if !strings.HasPrefix(baris, "- ") {
			continue
		}
		f := strings.TrimSpace(baris[2:])
		if f == "" || strings.HasPrefix(f, "_") {
			continue
		}
		hasil = append(hasil, f)
	}
	return hasil, nil
}

// SimpanFakta menulis ulang berkas fakta.
func (v *CharacterVault) SimpanFakta(fakta []string) error {
	const panduan = "Setiap baris di bawah masuk ke prompt sebagai sesuatu yang **dia ingat benar**.\n" +
		"Hanya simpan yang pernah Master tulis sendiri atau yang terukur dari mesin ini.\n\n"
	isi := panduan + "_Belum ada fakta tersimpan._"
	if len(fakta) > 0 {
		baris := make([]string, 0, len(fakta))
		for _, f := range fakta {
			baris = append(baris, "- "+f)
		}
		isi = panduan + strings.Join(baris, "\n")
	}
	return v.tulis("Fakta.md", kerangka("fakta-silverwolf",
		"Fakta yang Silver Wolf ingat tentang Master", isi, []string{"Mood", "Riwayat"}))
}

var (
	polaValensi    = regexp.MustCompile(`Valensi: (-?[\d.]+)`)
	polaEnergi     = regexp.MustCompile(`Energi: (-?[\d.]+)`)
	polaAfinitas   = regexp.MustCompile(`Afinitas: (-?[\d.]+)`)
	polaPertukaran = regexp.MustCompile(`Pertukaran tercatat: (\d+)`)
)

// BacaMood membaca mood terakhir dari berkas Mood.md; nil bila belum ada/valid.
func (v *CharacterVault) BacaMood() (*Mood, error) {
	teks, err := v.baca("Mood.md")
	if err != nil || teks == "" {
		return nil, err
	}
	ambil := func(pola *regexp.Regexp) (float64, bool) {
		m := pola.FindStringSubmatch(teks)
		if m == nil {
			return 0, false
		}
		n, err := strconv.ParseFloat(m[1], 64)
		if err != nil {
			return 0, false
		}
		return n, true
	}
	valensi, okV := ambil(polaValensi)
	energi, okE := ambil(polaEnergi)
	afinitas, okA := ambil(polaAfinitas)
	if !okV || !okE || !okA {
		return nil, nil
	}
	pertukaran := 0
	if m := polaPertukaran.FindStringSubmatch(teks); m != nil {
		if n, err := strconv.Atoi(m[1]); err == nil {
			pertukaran = n
		}
	}
	return &Mood{Valensi: valensi, Energi: energi, Afinitas: afinitas, Pertukaran: pertukaran}, nil
}

// SimpanMood menulis mood terakhir.
func (v *CharacterVault) SimpanMood(mood Mood) error {
	baris := []string{
		fmt.Sprintf("Valensi: %.2f (-1 berat .. +1 senang)", mood.Valensi),
		fmt.Sprintf("Energi: %.2f", mood.Energi),
		fmt.Sprintf("Afinitas: %.2f (0 jauh .. 1 dekat)", mood.Afinitas),
		fmt.Sprintf("Pertukaran tercatat: %d", mood.Pertukaran),
		"Terakhir diperbarui: " + time.Now().UTC().Format(time.RFC3339),
	}
	if mood.Alasan != "" {
		baris = append(baris, "Alasan: "+mood.Alasan)
	}
	return v.tulis("Mood.md", kerangka("mood-silverwolf",
		"Suasana hati Silver Wolf saat ini", strings.Join(baris, "\n"), []string{"Fakta", "Riwayat"}))
}

// CatatHari menambahkan satu baris ke riwayat percakapan hari ini.
func (v *CharacterVault) CatatHari(baris string) error {
	nama := "Riwayat/" + tanggal(time.Now()) + ".md"
	lama, err := v.baca(nama)
	if err != nil {
		return err
	}
	badan := []string{}
	for _, b := range strings.Split(lama, "\n") {
		if strings.HasPrefix(b, "- ") {
			badan = append(badan, b)
		}
	}
	badan = append(badan, "- "+baris)
	hari := tanggal(time.Now())
	return v.tulis(nama, kerangka("riwayat-"+hari, "Riwayat percakapan "+hari,
		strings.Join(badan, "\n"), []string{"Fakta", "Mood", "Riwayat"}))
}
