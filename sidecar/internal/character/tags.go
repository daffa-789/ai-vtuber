package character

import (
	"regexp"
	"strings"
)

// Kelas spasi dipakai supaya perilakunya sama dengan `\s` di JS (yang juga
// mencakup spasi unicode seperti U+00A0 dan U+3000).
const spasi = `\s   -     　`

var tagAwal = regexp.MustCompile("^[" + spasi + "`'\"]*\\[{1,2}([a-zA-Z][^\\n\\[\\]{}]{0,25})\\]\\]*[" + spasi + "`'\"]*")
var tagAsing = regexp.MustCompile("^[" + spasi + "`'\"]*\\[{1,2}([a-zA-Z][\\w:-]{0,24})\\]\\]*[" + spasi + "`'\"]*")

// BacaTagAwal membaca tag wajah di paling awal teks.
//
// `[[` di depan ditoleransi karena model 2B kadang menulis `[[senyum]`. Tanpa
// toleransi itu tag dikenali sebagai "asing", dibuang dari teks, tapi tag-nya
// hilang — raut wajah tidak pernah berubah walau model sudah menuliskannya.
func BacaTagAwal(teks string) string {
	m := tagAwal.FindStringSubmatch(teks)
	if m == nil {
		return ""
	}
	tag := strings.ToLower(strings.TrimSpace(m[1]))
	if !DikenalTag(tag) {
		return ""
	}
	return tag
}

// BersihkanTagAwal membuang tag wajah di awal teks.
//
//   - Tag yang **dikenal** mengembalikan `Tag` supaya mood/raut bisa diperbarui.
//   - Tag yang **tidak dikenal** tetap dibuang dari teks, tapi `Tag` tidak
//     diisi — supaya salah tulis model tidak merusak mood dan tidak ikut
//     diucapkan TTS. Isinya dibatasi: huruf diikuti huruf/angka/`_`/`-`/`:`
//     — jadi `arr[0]` atau `[1, 2, 3]` di awal kalimat tidak ikut kena.
func BersihkanTagAwal(teks string) struct {
	Teks string
	Tag  string
} {
	hasil := struct {
		Teks string
		Tag  string
	}{Teks: teks}
	if tag := BacaTagAwal(teks); tag != "" {
		hasil.Teks = tagAwal.ReplaceAllString(teks, "")
		hasil.Tag = tag
		return hasil
	}
	if tagAsing.MatchString(teks) {
		hasil.Teks = tagAsing.ReplaceAllString(teks, "")
	}
	return hasil
}
