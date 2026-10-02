// Package character memuat persona, mood, tag wajah, perakitan prompt, dan
// vault memori karakter. Ini adalah port dari `packages/core-character/src`.
package character

// EMOTION_TAGS adalah sembilan tag wajah yang boleh dipakai Silver Wolf;
// namanya = tag di persona.md.
var EMOTION_TAGS = []string{
	"netral", "senyum", "semangat", "kaget", "bingung", "lelah", "goda", "sebal", "sedih",
}

// Mood adalah suasana hati karakter yang tersimpan di vault.
type Mood struct {
	Valensi    float64
	Energi     float64
	Afinitas   float64
	Pertukaran int
	Alasan     string
}

// MOOD_AWAL adalah mood saat vault belum punya berkas Mood.md.
var MOOD_AWAL = Mood{Valensi: 0.2, Energi: 0.6, Afinitas: 0.3, Pertukaran: 0}

var nilaiTag = map[string]float64{
	"senyum": 0.25, "semangat": 0.35, "goda": 0.2, "netral": 0, "bingung": -0.05,
	"kaget": 0, "lelah": -0.2, "sedih": -0.3, "sebal": -0.25,
}

func jepit(n, min, maks float64) float64 {
	if n < min {
		return min
	}
	if n > maks {
		return maks
	}
	return n
}

// DikenalTag melaporkan apakah sebuah nama termasuk tag yang dikenal.
func DikenalTag(nama string) bool {
	for _, t := range EMOTION_TAGS {
		if t == nama {
			return true
		}
	}
	return false
}

// PerbaruiMood menggeser mood menurut tag emosi terakhir.
func PerbaruiMood(lama *Mood, tag string) Mood {
	dasar := MOOD_AWAL
	if lama != nil {
		dasar = *lama
	}
	delta := 0.0
	if tag != "" {
		if v, ok := nilaiTag[tag]; ok {
			delta = v
		}
	}
	tambahEnergi := 0.0
	if tag == "semangat" {
		tambahEnergi = 0.1
	}
	alasan := "tag terakhir: "
	if tag == "" {
		alasan += "tidak ada"
	} else {
		alasan += tag
	}
	return Mood{
		Valensi:    jepit(dasar.Valensi*0.8+delta*0.5, -1, 1),
		Energi:     jepit(dasar.Energi*0.95+tambahEnergi-0.02, 0, 1),
		Afinitas:   jepit(dasar.Afinitas+0.03, 0, 1),
		Pertukaran: dasar.Pertukaran + 1,
		Alasan:     alasan,
	}
}

// Suasana menerjemahkan mood menjadi satu kalimat arah nada untuk prompt.
func Suasana(mood *Mood) string {
	if mood == nil {
		return ""
	}
	if mood.Valensi < -0.25 {
		return "Kamu lagi agak berat hari ini, jadi jawabanmu lebih pendek dan lebih jujur."
	}
	if mood.Valensi > 0.3 && mood.Energi > 0.5 {
		return "Kamu lagi ceria, boleh lebih usil sedikit."
	}
	if mood.Energi < 0.3 {
		return "Kamu lagi capek, bicaranya lebih pelan dan pendek."
	}
	return ""
}
