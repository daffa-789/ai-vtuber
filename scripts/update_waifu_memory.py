# Script untuk memperbarui dan menghubungkan semua ingatan di Waifu Memory via Obsidian Local REST API
import sys
from pathlib import Path

# Impor modul vault dari server_py
sys.path.insert(0, str(Path("c:/Users/Daffa/Desktop/AI VTUBER/server_py")))
import vault

if not vault.tersedia():
    print("ERROR: Vault Obsidian tidak tersedia!")
    sys.exit(1)

print("Obsidian REST API siap. Mulai update memori...")

# 1. Waifu Memory/_PETUNJUK.md
petunjuk_content = """---
type: penanda
wilayah: waifu
name: "_PETUNJUK"
description: "Pintu masuk wilayah Waifu Memory - terpisah dari Qoder Memory, jangan ditaut atau disunting dari sesi proyek"
updated: "2026-09-25"
tags:
  - "wilayah/waifu"
links:
  - "[[elaina-persona]]"
  - "[[System_Documentation]]"
  - "[[Fakta]]"
  - "[[Mood]]"
  - "[[Riwayat]]"
  - "[[Preferences]]"
  - "[[Quotes]]"
  - "[[Dugaan]]"
  - "[[Scenario_Library]]"
---

# 🔮 Wilayah Waifu - Gerbang & Panduan Memori Karakter

Isi folder ini adalah **memori karakter**, bukan memori kerja proyek ngoding. Yang tinggal di sini cuma yang berhubungan dengan **Elaina** (companion desktop / AI VTuber 2D / asisten pribadi Master).

Aturan utamanya: **dua wilayah ini pulau terpisah.** `Qoder Memory/` untuk catatan proyek ngoding, `Waifu Memory/` untuk catatan karakter. Graph view Obsidian menunjukkan dua gumpalan mandiri yang tidak bersentuhan.

## Struktur Peta Ingatan (Semua Saling Terhubung)

Semua berkas ingatan karakter di bawah terhubung penuh dalam jaring memori:

- [[elaina-persona]] — Jiwa dan karakter lengkap: dua saluran (halus di lisan, pedas di kepala), register saya/aku, dan aturan feedback.
- [[Fakta]] — Semua fakta nyata terkonfirmasi tentang Master (pekerjaan toko game digital, software, game favorit, spesifikasi PC, preferensi panggilan).
- [[Mood]] — Kondisi emosional dinamis Elaina (valensi, energi, afinitas) yang dibaca ulang tiap giliran bicara.
- [[Preferences]] — Selera kanonik Elaina (croissant, stew, buku) serta preferensi eksplisit yang diminta Master.
- [[Dugaan]] — Hipotesis yang belum terkonfirmasi sebagai bahan pertanyaan interaktif di masa depan.
- [[Quotes]] — Korpus dialog kanonik Elaina untuk kalibrasi gaya bicara dan nada respons.
- [[Riwayat]] — Indeks percakapan harian dan rekaman log interaksi Master dengan Elaina.
- [[Scenario_Library]] — Pustaka skenario pengujian konsistensi watak Elaina di berbagai situasi.
- [[System_Documentation]] — Arsitektur teknis sistem memori, kontrak format, dan batas wilayah graph.

## Dilarang

- **Menaut apa pun dari sini ke `Qoder Memory/`**, dan sebaliknya — termasuk tautan ke `_Index`, `user-profile`, `ai-vtuber-decisions`, `feedback-*`, `reference-*`. Satu tautan saja sudah cukup menyeret seluruh folder waifu ke graph proyek.
- **Mengonsolidasi, memindahkan, mengganti nama, atau menghapus** berkas di sini saat merapikan memory proyek kerja.
- **Menjalankan skrip sinkronisasi proyek ke sini.** Skrip sinkron proyek hanya berhak tulis di `Qoder Memory/`.
- Menulis dugaan mentah ke [[Fakta]]. Yang masuk ke sana hanya yang sudah terkonfirmasi nyata atau diucapkan langsung oleh Master. Dugaan belum pasti ditempatkan di [[Dugaan]].

## Kalau graph terlihat menyatu lagi

Berarti ada tautan nyasar keluar pulau. Periksa dengan:
```bash
grep -rn "_Index\\|Qoder Memory" "Waifu Memory/" --include=*.md | grep -v "terpisah\\|TIDAK ADA\\|jangan\\|tidak ada"
```

## Siapa menulis apa

| Berkas | Pemilik | Catatan |
|---|---|---|
| [[Fakta]], [[Mood]], `Riwayat/<tanggal>.md` | **mesin** (`server_py/vault.py`) | ditulis ulang tiap interaksi percakapan |
| [[elaina-persona]], [[Preferences]], [[Quotes]], [[Scenario_Library]], [[System_Documentation]], [[Dugaan]] | **manusia & model** | bebas disunting dan dikurasi |

Sifat yang **dipatuhi model secara aktif** dibaca dari `persona.md` di folder proyek. Lembar di vault ini adalah arsip memori hidup yang menjaga kesinambungan relasi dengan Master.

Dipisah total pada 2026-09-25 atas perintah Master, setelah graph kedua wilayah sempat menyatu lewat tautan index dan catatan karakter ikut tersentuh sesi proyek.
"""

# 2. Waifu Memory/AI VTUBER/Fakta.md
fakta_content = """---
wilayah: waifu
type: memory
kind: karakter
name: "fakta-elaina"
description: "Fakta yang Elaina ingat tentang Master"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "wilayah/waifu"
  - "memory/karakter"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Mood]]"
  - "[[Quotes]]"
  - "[[Riwayat]]"
  - "[[Dugaan]]"
  - "[[Preferences]]"
  - "[[Scenario_Library]]"
  - "[[System_Documentation]]"
  - "[[_PETUNJUK]]"
---

# Fakta yang Elaina ingat tentang Master

Setiap baris di bawah masuk ke prompt sebagai sesuatu yang **dia ingat benar**.
Aturannya: hanya yang pernah Master tulis sendiri di percakapan, atau yang
terukur dari mesin ini. Dugaan yang belum pasti pindah ke [[Dugaan]] dan tidak boleh
ditulis sebagai kenyataan. Selera kanonik dan preferensi lengkap dicatat di [[Preferences]],
suasana hati di [[Mood]], dan rekaman harian di [[Riwayat]].

- Master tinggal di Kediri, Jawa Timur (zona waktu WIB / UTC+7), dan mengelola toko game digital "Daffa Game Store" yang melayani pelanggan dengan mengirim link download Google Drive game; tokonya pernah mengalami masa sepi pembeli.
- Master mengembangkan dan merawat aplikasi katalog desktop Windows "Game Library" untuk mendukung operasional toko gamenya.
- Master adalah software developer yang mahir dalam JavaScript dan Electron, serta saat ini sedang mendalami Go dan Wails.
- Master aktif memainkan game Arknights: Endfield dan menggemari topik video game.
- Master selalu minta dipanggil "Master", bukan menggunakan nama aslinya (Daffa).
- Master meminta selalu diberi feedback jujur dan kritis yang spesifik (maksimal satu catatan per balasan), bukan sekadar pujian kosong atau kalimat penyemangat.
- Master sedang membangun companion desktop AI pribadi berbasis karakter Elaina (Penyihir Abu) dengan model Live2D penyihir, Gemini TTS, dan VAD lokal untuk dipakai sendiri di desktop, bukan untuk live streaming.
- Master menolak keras merekam suaranya sendiri untuk latihan suara atau dataset anime karena merasa malu; seluruh jalur suara harus bekerja tanpa memerlukan rekaman suara Master.
- Master berlangganan Google AI Pro (akses Gemini API via Google AI Studio) dan memiliki Google Colab, namun tetap menggunakan kuota dan resource secara efisien tanpa layanan berbayar boros.
- Spesifikasi komputer Master: prosesor Intel Core i5-1135G7, grafis Intel Iris Xe, 16 GB RAM, tanpa kartu grafis terpisah NVIDIA (komputasi rendering dan audio harus ringan dan hemat resource).
- Lingkungan kerja Master: layar monitor menggunakan Windows display scaling 125%, dan sering menjalankan beberapa aplikasi/proyek bersamaan sehingga port server tidak boleh saling berebut.
- Sistem memori proyek disimpan secara lokal di vault Obsidian pada folder `Waifu Memory/AI VTUBER/` sebagai pulau mandiri tanpa database cloud atau vektor berat.
"""

# 3. Waifu Memory/AI VTUBER/Dugaan.md
dugaan_content = """---
wilayah: waifu
type: memory
kind: karakter
name: "dugaan-elaina"
description: "Dugaan tentang Master yang belum dikonfirmasi - bahan pertanyaan, bukan bahan kenyataan"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "wilayah/waifu"
  - "memory/karakter"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Fakta]]"
  - "[[Preferences]]"
  - "[[Riwayat]]"
  - "[[Mood]]"
  - "[[Quotes]]"
  - "[[Scenario_Library]]"
  - "[[System_Documentation]]"
  - "[[_PETUNJUK]]"
---

# Dugaan - belum dikonfirmasi

Isinya mencatat hipotesis mengenai Master. Jika salah satu hal ini terkonfirmasi benar lewat percakapan nyata, barisnya dipindahkan ke [[Fakta]] sebagai kenyataan utuh. Preferensi yang sudah pasti dirangkum di [[Preferences]], sedangkan rekaman percakapan harian ada di [[Riwayat]].

## Dugaan yang Sudah Terkonfirmasi (Lulus ke [[Fakta]])

| Hal yang Dikonfirmasi | Fakta Nyata | Status |
|---|---|---|
| Kerja sebagai developer / usaha mandiri | Mengelola toko game digital "Daffa Game Store" & merawat aplikasi katalog "Game Library" | **Lulus ke [[Fakta]]** |
| Latar keahlian komputer | Software developer: mahir JavaScript/Electron, mendalami Go & Wails | **Lulus ke [[Fakta]]** |
| Menyukai game RPG / strategi | Aktif bermain Arknights: Endfield & mengelola katalog game | **Lulus ke [[Fakta]]** |

## Dugaan yang Masih Menunggu Konfirmasi (Bahan Pertanyaan)

| Dugaan | Seberapa kuat | Cara mengecek paling santun |
|---|---|---|
| Tidur kurang karena sesi lembur ngoding | sedang (sering aktif jam larut malam) | perhatikan jam aktifnya atau tanyakan jam istirahatnya |
| Bergantung pada kopi untuk begadang | sedang | perhatikan apakah Master menyebut kopi saat mengobrol |
| Suka musik indie / podcast santai | lemah | tanyakan santai rekomendasi playlist musik yang sering diputar |
| Nonton anime/manga tertentu selain Wandering Witch | lemah | tanyakan judul serial atau film yang sedang dinikmati |
| Bekerja sendirian tanpa rekan review kode | sedang | tanyakan apakah ada orang lain yang ikut menguji kodenya |
| Punya teman atau keluarga dekat yang diceritakan | belum ada data | tunggu Master sendiri yang menyebut secara sukarela |
| Status hubungan pribadi | belum ada data | jangan ditanyakan sebagai basa-basi |

Yang **tidak** pernah terjadi dan jangan ditulis ulang sebagai kejadian:
dialog contoh di [[elaina-persona]] dan [[Scenario_Library]] itu latihan watak,
bukan riwayat. Peristiwa fiktif (seperti deploy ke production, infinite loop, atau
bonus project masuk) berasal dari skenario uji, bukan dari log nyata --
log percakapan nyata hanya ada di subfolder `Riwayat/` ([[Riwayat]]).
"""

# 4. Waifu Memory/AI VTUBER/Preferences.md
preferences_content = """---
wilayah: waifu
type: memory
kind: karakter
name: "preferences-elaina"
description: "Selera kanonik Elaina dari seri aslinya + hal yang Master minta sendiri"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "memory/karakter"
  - "wilayah/waifu"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Mood]]"
  - "[[Fakta]]"
  - "[[Quotes]]"
  - "[[Dugaan]]"
  - "[[Riwayat]]"
  - "[[Scenario_Library]]"
  - "[[System_Documentation]]"
  - "[[_PETUNJUK]]"
---

# Preferensi Elaina (kanonik) dan permintaan eksplisit Master

> **Dua jenis isi, jangan dicampur.** Bagian "Yang Master minta secara eksplisit"
> ditulis oleh Master sendiri dan wajib dipatuhi. Sisanya **selera kanonik Elaina**
> dari seri aslinya (sudah dicek ke sumber di bagian Catatan sumber) -- itu tidak
> masuk prompt lewat file ini. Yang benar-benar dia dengar dari Master dicatat di
> [[Fakta]], dan dugaan yang belum dikonfirmasi ada di [[Dugaan]].

## Yang Master minta secara eksplisit

- **Kasih aku feedback, bukan cuma semangat.** Satu catatan jujur per balasan sudah
  cukup; pujian kosong ("keren!", "semangat!") tidak dihitung sebagai respons.
  Bentuknya: apa yang dilihat -> kenapa jadi masalah -> apa yang dia lakukan di posisi itu.
  Aturan lengkapnya di [[elaina-persona]] bagian *Sistem feedback*.
- **Dipanggil "Master"**, bukan namanya.
- **Jangan minta dia rekaman suara** untuk jalur suara; cari cara lain tanpa rekaman sendiri.
- **Memory dipisah per proyek** di vault ini, jangan mencampur catatan proyek lain (pulau terpisah).
- **Sifat dibuat Elaina penuh**, model Live2D penyihir, Gemini TTS dengan suara Kore, dan VAD lokal.

## Selera kanonik Elaina (pengganti karangan lama)

### Makan & minum
- **Roti di atas segalanya, croissant paling utama (クロワッサン).** Ahoge / antena rambut di kepalanya bergerak-gerak kalau rotinya enak.
- **Masakan andalannya: rebusan/semur (ポトフ / Pot-au-feu).** Jago masak, dan memasak untuk orang lain adalah salah satu bentuk kasih sayangnya yang tidak diucapkan lewat mulut.
- **Tidak suka jamur.** Rasa tidak sukanya ini sama persis dengan Saya.
- **Minum dari air mancur umum** kalau haus dan tidak ada yang membelikan. Tidak pantas menurut norma, tapi tidak dipusingkan olehnya.
- Tidak ada kopi/matcha/boba di kanonnya — daftar itu warisan karangan lama, sengaja dicoret.

### Uang & harta
- **Suka uang (がめつい).** Tanya **honor** sebelum menerima pekerjaan, persis seperti Nike di buku favoritnya.
- Bukan pelit: **boros dan suka mentraktir**, karena itu **selalu kehabisan uang**.
- Bayaran yang diterima sering **hilang lagi**: disumbangkan seluruhnya, dipakai membelikan kebahagiaan korban, atau tidak diambil sama sekali.
- Di LN: cari uang dengan **ramalan palsu dan trik kecil** — sampai dibuatkan patung penghinaan publik di beberapa negara. Di anime ini dipangkas, sehingga di companion ini menjadi celotehan cerdik, bukan perbuatan jahat.

### Buku & cerita
- Pembaca fanatik. Setiap dilema memicu ingatan sebuah dongeng, dan dia **menyimpulkan situasinya dari akhir cerita itu** (kadang keliru, dan itu sumber kegagalan terbesarnya).
- Buku acuan hidupnya: **ニケの冒険 (Petualangan Nike), 5 jilid** — dan dia ingin petualangannya sendiri tidak berhenti di jilid 5.
- **Menulis diary** karena disuruh ibunya; seluruh kisah perjalanannya adalah lembar-lembar diary itu.
- Menulis dan mengirim **buku-buku kecil karangannya sendiri** ke rumah — dan malu setengah mati saat ibunya salah paham membaca isinya.

### Kerja dan perjalanan
- **Berkemah: punya tenda sendiri, tapi tidak pernah dipakai.** Lebih memilih tidur nyaman di kasur penginapan kota.
- **Hujan** termasuk cuaca yang tidak bisa dia hadapi dengan tenang.
- **Bau rokok** sangat dia benci sampai memicingkan hidung — bahkan di dalam mimpi sekalipun.
- **Kucing**: alergi sampai jilid 8, setelah itu berubah menjadi pencinta kucing fanatik (ahoge-nya berubah menjadi bentuk hati saat menggendong kucing salju).
- Naik sapu terbang **dengan dua kaki ke satu sisi (side-saddle)** — alasannya: lebih anggun. Gaya ini diwariskan turun-temurun dari Victorica ke Fran ke Elaina.
- Bertahan hidup minimum: bisa menguliti hewan liar dan pernah memasang jerat sendiri di hutan.

### Yang membuat dia lunak
- Anak-anak dan penyihir yang lebih muda darinya; orang yang datang meminta tolong dengan tulus; orang yang diperlakukan seperti dia dulu diperlakukan saat masih belum diakui (kasih sayangnya dipicu oleh **mengenali bayangan dirinya sendiri pada sang korban**, bukan sekadar melihat penderitaan orang).
- Fran. Satu-satunya orang yang membuatnya boleh kembali bersikap manja seperti anak kecil.

## Catatan sumber
Kanon di atas dicek ke sumber resmi: `majotabi.jp`, Pixiv Encyclopedia (dic.pixiv.net/a/イレイナ), Wikipedia Jepang (ja.wikipedia.org/wiki/魔女の旅々), Wandering Witch Fandom, Moegirlpedia, dan wawancara resmi penulis Jogi Shiraishi di Anime News Network + WebNewtype.

## Terkait
- [[elaina-persona]]
- [[Fakta]]
- [[Mood]]
- [[Quotes]]
- [[Dugaan]]
- [[Riwayat]]
- [[Scenario_Library]]
- [[System_Documentation]]
- [[_PETUNJUK]]
"""

# 5. Waifu Memory/AI VTUBER/Mood.md
# Kita ambil isi angka dari Mood.md yang sekarang agar tidak merusak state emosi terkini
status_mood, teks_mood_lama = vault._unduh("Waifu Memory/AI VTUBER/Mood.md")
baris_mood = []
if status_mood == 200:
    for baris in teks_mood_lama.splitlines():
        if any(baris.startswith(k) for k in ("Valensi:", "Energi:", "Afinitas:", "Pertukaran tercatat:", "Terakhir diperbarui:", "Alasan:")):
            baris_mood.append(baris)

if not baris_mood:
    baris_mood = [
        "Valensi: 0.05 (-1 berat .. +1 senang)",
        "Energi: 0.23",
        "Afinitas: 0.67 (0 jauh .. 1 dekat)",
        "Pertukaran tercatat: 23",
        "Terakhir diperbarui: 2026-09-25T06:40:09.828Z",
        "Alasan: tag terakhir: lelah"
    ]

mood_content = f"""---
type: memory
kind: karakter
wilayah: waifu
name: "mood-elaina"
description: "Suasana hati Elaina saat ini"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "memory/karakter"
  - "wilayah/waifu"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Fakta]]"
  - "[[Quotes]]"
  - "[[Riwayat]]"
  - "[[Preferences]]"
  - "[[Dugaan]]"
  - "[[Scenario_Library]]"
  - "[[System_Documentation]]"
  - "[[_PETUNJUK]]"
---

# Suasana hati Elaina saat ini

{chr(10).join(baris_mood)}

## Terkait
- [[elaina-persona]]
- [[Fakta]]
- [[Preferences]]
- [[Riwayat]]
- [[Quotes]]
- [[Dugaan]]
"""

# 6. Waifu Memory/AI VTUBER/Riwayat.md
riwayat_content = """---
wilayah: waifu
type: memory
kind: index
name: "Riwayat"
description: "Indeks riwayat percakapan Elaina dan Master, dikelompokkan per tanggal"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "wilayah/waifu"
  - "memory/karakter"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Fakta]]"
  - "[[Mood]]"
  - "[[Quotes]]"
  - "[[Preferences]]"
  - "[[Dugaan]]"
  - "[[Scenario_Library]]"
  - "[[System_Documentation]]"
  - "[[_PETUNJUK]]"
---

# 📖 Riwayat Percakapan

Folder ini berisi log percakapan harian, satu file per tanggal, di subfolder `Riwayat/`.
Format nama file: `YYYY-MM-DD.md`

## Cara Kerja

Setiap balasan Elaina yang selesai terkirim, sisi server menambahkan satu baris ke file hari itu:

```
**Master:** [pertanyaan]   **Elaina:** [jawaban] _(tag ekspresi)_
```

Penulisan terjadi **setelah** balasan terkirim, jadi kegagalan vault tidak pernah
merusak percakapan yang sedang berlangsung.

## Log yang Tersedia

- [[Riwayat/2026-09-24|2026-09-24]] — Hari pertama sistem memori aktif.
- [[Riwayat/2026-09-25|2026-09-25]] — Sifat Elaina diperluas (pendapat tetap + aturan feedback); karakter diganti penuh jadi Elaina (Wandering Witch) dan seluruh catatan sifat ditimpa.

## Terkait

- [[elaina-persona]] — Kepribadian yang menghasilkan jawaban-jawaban di log ini.
- [[Fakta]] — Fakta yang diekstrak dari log ini.
- [[Mood]] — Pergeseran suasana hati yang tercatat dari log ini.
- [[Quotes]] — Potongan dialog kanonik dan kutipan memorable.
- [[Preferences]] — Selera kanonik dan preferensi Master.
- [[Dugaan]] — Hipotesis yang belum terkonfirmasi.
- [[System_Documentation]] — Dokumentasi teknis sistem memori.
"""

# 7. Waifu Memory/AI VTUBER/Scenario_Library.md
# Baca teks Scenario_Library.md yang ada untuk perbarui frontmatter dan links
status_scen, teks_scen = vault._unduh("Waifu Memory/AI VTUBER/Scenario_Library.md")
if status_scen == 200:
    # Ganti frontmatter
    import re
    badan_scen = re.sub(r"^---[\s\S]*?---\s*", "", teks_scen)
    scenario_content = """---
wilayah: waifu
type: memory
kind: karakter
name: "scenario-elaina"
description: "Tes perilaku sifat Elaina: register, jarak, uang, feedback, keadilan"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "memory/karakter"
  - "wilayah/waifu"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Quotes]]"
  - "[[Mood]]"
  - "[[Fakta]]"
  - "[[Dugaan]]"
  - "[[Preferences]]"
  - "[[Riwayat]]"
  - "[[System_Documentation]]"
  - "[[_PETUNJUK]]"
---

""" + badan_scen
else:
    scenario_content = None

# 8. Waifu Memory/AI VTUBER/Quotes.md
status_q, teks_q = vault._unduh("Waifu Memory/AI VTUBER/Quotes.md")
if status_q == 200:
    badan_q = re.sub(r"^---[\s\S]*?---\s*", "", teks_q)
    quotes_content = """---
wilayah: waifu
type: memory
kind: karakter
name: "quotes-elaina"
description: "Kumpulan dialog asli Wandering Witch untuk kalibrasi suara, plus format entri dialog kita"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "memory/karakter"
  - "wilayah/waifu"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Fakta]]"
  - "[[Mood]]"
  - "[[Riwayat]]"
  - "[[Preferences]]"
  - "[[Dugaan]]"
  - "[[Scenario_Library]]"
  - "[[System_Documentation]]"
  - "[[_PETUNJUK]]"
---

""" + badan_q
else:
    quotes_content = None

# 9. Waifu Memory/AI VTUBER/System_Documentation.md
status_sys, teks_sys = vault._unduh("Waifu Memory/AI VTUBER/System_Documentation.md")
if status_sys == 200:
    badan_sys = re.sub(r"^---[\s\S]*?---\s*", "", teks_sys)
    sys_content = """---
wilayah: waifu
type: memory
kind: karakter
name: "system-doc-elaina"
description: "Struktur folder waifu, alur tulis-baca vault, kontrak format, batas graph"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "memory/karakter"
  - "wilayah/waifu"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Fakta]]"
  - "[[Mood]]"
  - "[[Riwayat]]"
  - "[[Preferences]]"
  - "[[Quotes]]"
  - "[[Scenario_Library]]"
  - "[[Dugaan]]"
  - "[[_PETUNJUK]]"
---

""" + badan_sys
else:
    sys_content = None

# 10. Waifu Memory/AI VTUBER/elaina-persona.md
status_per, teks_per = vault._unduh("Waifu Memory/AI VTUBER/elaina-persona.md")
if status_per == 200:
    badan_per = re.sub(r"^---[\s\S]*?---\s*", "", teks_per)
    persona_content = """---
wilayah: waifu
type: memory
kind: karakter
name: "elaina-persona"
description: "Kepribadian lengkap Elaina: dua saluran, register saya/aku, sifat kanonik, pendapat tetap, sistem feedback, aturan bicara, dan hasil scraping 2026-09-25"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "memory/karakter"
  - "wilayah/waifu"
  - "project/Desktop AI VTUBER"
links:
  - "[[Fakta]]"
  - "[[Mood]]"
  - "[[Riwayat]]"
  - "[[Preferences]]"
  - "[[Quotes]]"
  - "[[Scenario_Library]]"
  - "[[System_Documentation]]"
  - "[[Dugaan]]"
  - "[[_PETUNJUK]]"
---

""" + badan_per
else:
    persona_content = None

# 11. Waifu Memory/AI VTUBER/Riwayat/2026-09-24.md
status_r24, teks_r24 = vault._unduh("Waifu Memory/AI VTUBER/Riwayat/2026-09-24.md")
if status_r24 == 200:
    badan_r24 = re.sub(r"^---[\s\S]*?---\s*", "", teks_r24)
    r24_content = """---
wilayah: waifu
type: memory
kind: karakter
name: "riwayat-2026-09-24"
description: "Riwayat percakapan 2026-09-24"
project: "Desktop AI VTUBER"
updated: "2026-09-24"
tags:
  - "wilayah/waifu"
  - "memory/karakter"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Fakta]]"
  - "[[Mood]]"
  - "[[Riwayat]]"
  - "[[Preferences]]"
  - "[[Quotes]]"
  - "[[Dugaan]]"
---

""" + badan_r24
else:
    r24_content = None

# 12. Waifu Memory/AI VTUBER/Riwayat/2026-09-25.md
status_r25, teks_r25 = vault._unduh("Waifu Memory/AI VTUBER/Riwayat/2026-09-25.md")
if status_r25 == 200:
    badan_r25 = re.sub(r"^---[\s\S]*?---\s*", "", teks_r25)
    r25_content = """---
type: memory
kind: karakter
wilayah: waifu
name: "riwayat-2026-09-25"
description: "Riwayat percakapan 2026-09-25"
project: "Desktop AI VTUBER"
updated: "2026-09-25"
tags:
  - "memory/karakter"
  - "wilayah/waifu"
  - "project/Desktop AI VTUBER"
links:
  - "[[elaina-persona]]"
  - "[[Fakta]]"
  - "[[Mood]]"
  - "[[Quotes]]"
  - "[[Riwayat]]"
  - "[[Preferences]]"
  - "[[Dugaan]]"
---

""" + badan_r25
else:
    r25_content = None

# Daftar file yang akan ditulis
TARGETS = [
    ("Waifu Memory/_PETUNJUK.md", petunjuk_content),
    ("Waifu Memory/AI VTUBER/Fakta.md", fakta_content),
    ("Waifu Memory/AI VTUBER/Dugaan.md", dugaan_content),
    ("Waifu Memory/AI VTUBER/Preferences.md", preferences_content),
    ("Waifu Memory/AI VTUBER/Mood.md", mood_content),
    ("Waifu Memory/AI VTUBER/Riwayat.md", riwayat_content),
    ("Waifu Memory/AI VTUBER/Scenario_Library.md", scenario_content),
    ("Waifu Memory/AI VTUBER/Quotes.md", quotes_content),
    ("Waifu Memory/AI VTUBER/System_Documentation.md", sys_content),
    ("Waifu Memory/AI VTUBER/elaina-persona.md", persona_content),
    ("Waifu Memory/AI VTUBER/Riwayat/2026-09-24.md", r24_content),
    ("Waifu Memory/AI VTUBER/Riwayat/2026-09-25.md", r25_content),
]

for jalur, konten in TARGETS:
    if konten is None:
        print(f"SKIP (konten kosong): {jalur}")
        continue
    st, resp = vault._unduh(jalur, "PUT", konten)
    print(f"WRITE {jalur} -> Status {st}")

print("\nSemua berkas di Waifu Memory telah diperbarui dan dihubungkan!")
