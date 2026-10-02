// Package config memuat pembacaan `.env` dan koerser bertipe. Ini adalah port
// dari `packages/core-config/src/env-file.ts` dan `coerce.ts`, yang sendiri
// merupakan port dari `server_py/konfig.py`.
//
// ATURAN: setiap kunci dan nilai bawaan dipertahankan verbatim. Kalau sebuah
// kunci hilang dari sini, perilaku aplikasi berubah tanpa pesan — kelas bug yang
// sudah beberapa kali terjadi di proyek lama.
package config

import "strings"

// Bersih membuang kutip pembungkus bila ada (padanan `_bersih`).
func Bersih(nilai string) string {
	v := strings.TrimSpace(nilai)
	if len(v) >= 2 && v[0] == v[len(v)-1] && (v[0] == '"' || v[0] == '\'') {
		return v[1 : len(v)-1]
	}
	return v
}

// PotongKomentar adalah padanan `_potong_komentar`.
//
// Parser ini sengaja tidak memakai pustaka dotenv: perilaku di bawah adalah
// hasil perbaikan bug nyata di proyek lama (nilai seperti `99  # semua lapis`
// dulu terbaca utuh lalu diam-diam jatuh ke bawaan).
//
//   - nilai yang dikutip dipotong sampai kutip penutupnya saja;
//   - `#` hanya jadi komentar kalau didahului spasi/tab (jadi `#fff` dan resep
//     param tetap utuh).
func PotongKomentar(nilai string) string {
	mentah := strings.TrimSpace(nilai)
	if len(mentah) >= 2 && (mentah[0] == '"' || mentah[0] == '\'') {
		kutip := mentah[0]
		if akhir := strings.IndexByte(mentah[1:], kutip); akhir >= 0 {
			return mentah[1 : 1+akhir]
		}
		return mentah[1:]
	}
	for i := 0; i < len(mentah); i++ {
		if mentah[i] == '#' && i > 0 && (mentah[i-1] == ' ' || mentah[i-1] == '\t') {
			return strings.TrimRight(mentah[:i], " \t")
		}
	}
	return mentah
}

// BacaEnv mem-parse isi `.env`: `KUNCI=nilai`, `#` komentar, spasi di sekitar `=`.
func BacaEnv(isi string) map[string]string {
	hasil := map[string]string{}
	for _, barisMentah := range strings.Split(isi, "\n") {
		baris := strings.TrimSpace(strings.TrimSuffix(barisMentah, "\r"))
		if baris == "" || strings.HasPrefix(baris, "#") || !strings.Contains(baris, "=") {
			continue
		}
		idx := strings.IndexByte(baris, '=')
		kunci := strings.TrimSpace(baris[:idx])
		if kunci == "" {
			continue
		}
		hasil[kunci] = PotongKomentar(baris[idx+1:])
	}
	return hasil
}
