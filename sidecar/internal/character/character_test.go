package character

import (
	"strings"
	"testing"
	"time"
)

func TestBacaTagAwal(t *testing.T) {
	kasus := []struct {
		masuk string
		harap string
	}{
		{"[senyum] Beres, Master.", "senyum"},
		{"[[senyum]] Beres.", "senyum"},
		{"  [SEBAL]  Hai.", "sebal"},
		{"[kosong] tanpa daftar", ""},
		{"[1, 2, 3] angka di awal", ""},
		{"tanpa tag sama sekali", ""},
		{"arr[0] bukan tag", ""},
	}
	for _, k := range kasus {
		if dapat := BacaTagAwal(k.masuk); dapat != k.harap {
			t.Errorf("BacaTagAwal(%q) = %q, ingin %q", k.masuk, dapat, k.harap)
		}
	}
}

func TestBersihkanTagAwal(t *testing.T) {
	// Tag dikenal: dibuang dan dilaporkan supaya raut wajah bisa mengikuti.
	dapat := BersihkanTagAwal("[senyum] Beres, Master.")
	if dapat.Tag != "senyum" || dapat.Teks != "Beres, Master." {
		t.Errorf("tag dikenal = %+v, ingin teks 'Beres, Master.' + tag senyum", dapat)
	}
	// Tag asing: dibuang dari teks (biar tidak ikut diucapkan TTS), tapi tidak
	// mengubah mood.
	asing := BersihkanTagAwal("[Kegagalan] Sistem gagal.")
	if asing.Tag != "" {
		t.Errorf("tag asing tidak boleh mengisi Tag, dapat %q", asing.Tag)
	}
	if asing.Teks != "Sistem gagal." {
		t.Errorf("tag asing harus dibuang dari teks, dapat %q", asing.Teks)
	}
	// Teks tanpa tag tidak boleh berubah.
	polos := BersihkanTagAwal("Halo Master.")
	if polos.Teks != "Halo Master." || polos.Tag != "" {
		t.Errorf("teks polos = %+v, tidak boleh berubah", polos)
	}
}

func TestPerbaruiMood(t *testing.T) {
	mood := PerbaruiMood(nil, "semangat")
	if mood.Pertukaran != 1 {
		t.Errorf("Pertukaran = %d, ingin 1", mood.Pertukaran)
	}
	if mood.Valensi <= 0 {
		t.Errorf("Valensi setelah 'semangat' harus naik, dapat %v", mood.Valensi)
	}
	// Rentang harus selalu terjepit, berapa kali pun dipanggil.
	for i := 0; i < 200; i++ {
		mood = PerbaruiMood(&mood, "sedih")
	}
	if mood.Valensi < -1 || mood.Valensi > 1 || mood.Energi < 0 || mood.Energi > 1 || mood.Afinitas > 1 {
		t.Errorf("mood keluar rentang: %+v", mood)
	}
	if mood.Pertukaran != 201 {
		t.Errorf("Pertukaran = %d, ingin 201", mood.Pertukaran)
	}
}

func TestSuasana(t *testing.T) {
	if Suasana(nil) != "" {
		t.Error("mood nil harus menghasilkan string kosong")
	}
	berat := Suasana(&Mood{Valensi: -0.8, Energi: 0.5})
	if !strings.Contains(berat, "berat") {
		t.Errorf("suasana valensi rendah = %q", berat)
	}
	capek := Suasana(&Mood{Valensi: 0, Energi: 0.1})
	if !strings.Contains(capek, "capek") {
		t.Errorf("suasana energi rendah = %q", capek)
	}
	if Suasana(&Mood{Valensi: 0.1, Energi: 0.5}) != "" {
		t.Error("mood biasa tidak perlu kalimat suasana")
	}
}

func TestRingkasPersona(t *testing.T) {
	pendek := "## Aturan\nHalo."
	if dapat := RingkasPersona(pendek); dapat.Terpotong || dapat.Teks != pendek {
		t.Errorf("persona pendek tidak boleh berubah: %+v", dapat)
	}
	panjang := strings.Repeat("a", 18000) + "\n\n## Contoh Nada\nhilang"
	dapat := RingkasPersona(panjang)
	if !dapat.Terpotong {
		t.Error("persona panjang harus ditandai terpotong")
	}
	if len(dapat.BagianHilang) == 0 || dapat.BagianHilang[0] != "Contoh Nada" {
		t.Errorf("BagianHilang = %v, ingin memuat 'Contoh Nada'", dapat.BagianHilang)
	}
	// Pemotongan tidak boleh memecah paragraf di tengah.
	if strings.HasSuffix(dapat.Teks, "\n") {
		t.Error("hasil potongan tidak boleh menyisakan baris kosong di ujung")
	}
}

func TestGabungSystem(t *testing.T) {
	lokal := GabungSystem("PERSONA", []string{"fakta satu"}, &Mood{Valensi: 0.9, Energi: 0.9}, true)
	if !strings.Contains(lokal, "PERSONA") || !strings.Contains(lokal, "WAJIB") ||
		!strings.Contains(lokal, "- fakta satu") || !strings.Contains(lokal, "Suasana hatimu saat ini") {
		t.Errorf("prompt lokal kurang lengkap: %q", lokal)
	}
	// Hanya 5 fakta terakhir yang ikut di jalur lokal.
	banyak := []string{"1", "2", "3", "4", "5", "6", "7"}
	if dapat := GabungSystem("P", banyak, nil, true); strings.Contains(dapat, "- 1\n") {
		t.Error("jalur lokal hanya boleh memakai 5 fakta terakhir")
	}
	// Jalur non-lokal (Ollama) memakai semua fakta dan tanpa kontrak tag.
	nonLokal := GabungSystem("P", banyak, nil, false)
	if strings.Contains(nonLokal, "WAJIB") {
		t.Error("jalur non-lokal tidak boleh memakai kontrak tag emosi")
	}
	if !strings.Contains(nonLokal, "- 1\n") {
		t.Error("jalur non-lokal harus memakai seluruh fakta")
	}
}

func TestVaultFaktaDanMood(t *testing.T) {
	v := NewVault(t.TempDir())
	if v.Available() != true {
		t.Fatal("folder temp harus tersedia")
	}
	if dapat, err := v.BacaFakta(); err != nil || len(dapat) != 0 {
		t.Errorf("vault kosong = %v, %v", dapat, err)
	}
	if err := v.SimpanFakta([]string{"Master suka kopi", "Master benci emoji"}); err != nil {
		t.Fatalf("SimpanFakta: %v", err)
	}
	fakta, err := v.BacaFakta()
	if err != nil {
		t.Fatalf("BacaFakta: %v", err)
	}
	if len(fakta) != 2 || fakta[0] != "Master suka kopi" {
		t.Errorf("fakta = %v", fakta)
	}
	// Baris panduan yang diawali "_" tidak boleh ikut terbaca sebagai fakta.
	if err := v.SimpanFakta(nil); err != nil {
		t.Fatalf("SimpanFakta kosong: %v", err)
	}
	if dapat, _ := v.BacaFakta(); len(dapat) != 0 {
		t.Errorf("fakta kosong = %v, ingin tidak ada", dapat)
	}

	if mood, err := v.BacaMood(); err != nil || mood != nil {
		t.Errorf("mood awal = %v, %v; ingin nil", mood, err)
	}
	if err := v.SimpanMood(Mood{Valensi: 0.5, Energi: 0.4, Afinitas: 0.3, Pertukaran: 7, Alasan: "uji"}); err != nil {
		t.Fatalf("SimpanMood: %v", err)
	}
	mood, err := v.BacaMood()
	if err != nil {
		t.Fatalf("BacaMood: %v", err)
	}
	if mood == nil || mood.Pertukaran != 7 || mood.Valensi != 0.5 {
		t.Errorf("mood = %+v, ingin valensi 0.5 dan pertukaran 7", mood)
	}
}

func TestVaultCatatHari(t *testing.T) {
	v := NewVault(t.TempDir())
	for i := 0; i < 3; i++ {
		if err := v.CatatHari("Master: halo | Silver Wolf: hai"); err != nil {
			t.Fatalf("CatatHari: %v", err)
		}
	}
	// Baris lama harus tetap ada: riwayat ditambahkan, bukan ditimpa.
	isi, err := v.baca("Riwayat/" + tanggal(time.Now()) + ".md")
	if err != nil {
		t.Fatalf("baca riwayat: %v", err)
	}
	if strings.Count(isi, "- Master: halo") != 3 {
		t.Errorf("riwayat harus memuat 3 baris, isi: %s", isi)
	}
	if !strings.Contains(isi, "type: memory") {
		t.Error("kerangka frontmatter harus ikut tertulis")
	}
}

func TestVaultTidakTersedia(t *testing.T) {
	v := NewVault(t.TempDir() + "/tidak-ada")
	if v.Available() {
		t.Error("folder yang tidak ada tidak boleh dilaporkan tersedia")
	}
	if v.UnavailableReason() == "" {
		t.Error("alasan ketiadaan harus terisi")
	}
}

func TestBacaPersona(t *testing.T) {
	if _, err := BacaPersona(t.TempDir() + "/nama.md"); err == nil ||
		!strings.Contains(err.Error(), "persona tidak ditemukan") {
		t.Errorf("BacaPersona pada berkas yang hilang = %v, ingin 'persona tidak ditemukan'", err)
	}
}
