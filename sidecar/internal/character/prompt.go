package character

import (
	"regexp"
	"strings"
)

// RingkasanPersona adalah hasil pemotongan persona yang kepanjangan.
type RingkasanPersona struct {
	Teks         string
	Terpotong    bool
	BagianHilang []string
}

var judulPersona = regexp.MustCompile(`(?m)^## (.+)$`)

const batasPersona = 18000

// RingkasPersona memotong persona kalau kepanjangan, di batas paragraf.
//
// Batas 18.000 dipilih dari persona Silver Wolf yang sekarang (~15.200 karakter).
// Dengan batas lama 9.000, bagian terakhir — aturan larangan emoji dan contoh
// nada — ikut terbuang tanpa suara, sehingga model bebas menempelkan emoji.
//
// Persona ini juga disusun ulang pada 1 Okt: aturan keras (kontrak balasan,
// daftar tag wajah, batas perilaku) dipindah ke PALING ATAS. Jadi kalau suatu
// hari tetap kepotong, yang hilang cuma contoh nada — bukan aturannya.
func RingkasPersona(teks string) RingkasanPersona {
	rune_ := []rune(teks)
	if len(rune_) <= batasPersona {
		return RingkasanPersona{Teks: teks}
	}
	hasil := string(rune_[:batasPersona])
	if paragraf := strings.LastIndex(hasil, "\n\n"); paragraf > batasPersona/2 {
		hasil = hasil[:paragraf]
	}
	hilang := []string{}
	for _, m := range judulPersona.FindAllStringSubmatch(teks, -1) {
		judul := strings.TrimSpace(m[1])
		if judul != "" && !strings.Contains(hasil, "## "+judul) {
			hilang = append(hilang, judul)
		}
	}
	return RingkasanPersona{Teks: hasil, Terpotong: true, BagianHilang: hilang}
}

// GabungSystem merakit prompt sistem: persona + kontrak tag + fakta + suasana.
func GabungSystem(persona string, fakta []string, mood *Mood, lokal bool) string {
	bagian := []string{RingkasPersona(persona).Teks}
	if lokal {
		daftar := make([]string, 0, len(EMOTION_TAGS))
		for _, t := range EMOTION_TAGS {
			daftar = append(daftar, "["+t+"]")
		}
		bagian = append(bagian, "WAJIB: Awali setiap balasanmu dengan satu tag emosi di paling depan, persis satu dari "+
			strings.Join(daftar, ", ")+". Contoh: [senyum] Beres, Master. Tinggal bilang bagian mana yang macet.")
	}
	if len(fakta) > 0 {
		daftar := fakta
		if lokal && len(daftar) > 5 {
			daftar = daftar[len(daftar)-5:]
		}
		baris := make([]string, 0, len(daftar))
		for _, f := range daftar {
			baris = append(baris, "- "+f)
		}
		judul := "Fakta tentang Master"
		if !lokal {
			judul = "## Yang aku ingat tentang Master"
		}
		bagian = append(bagian, judul+":\n"+strings.Join(baris, "\n"))
	}
	if kini := Suasana(mood); kini != "" {
		judul := "Suasana hatimu saat ini"
		if !lokal {
			judul = "## Suasana hatiku sekarang"
		}
		bagian = append(bagian, judul+": "+kini)
	}
	return strings.Join(bagian, "\n\n")
}
