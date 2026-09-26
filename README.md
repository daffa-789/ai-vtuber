# AI VTuber

Teman desktop berbasis Live2D yang bisa diajak ngobrol lewat teks maupun suara,
menjawab dengan suara, dan menggerakkan wajah serta rahang sesuai isi pembicaraannya.

Status: renderer, loop chat, ekspresi, text-to-speech (lokal dan cloud), dan memori
jangka panjang sudah berjalan. Memory karakter ditulis sebagai catatan Markdown di
vault Obsidian, jadi bisa dibaca dan disunting langsung.

## Menjalankan

Prasyarat: **Python 3.10**. Tidak ada Node lagi di proyek ini — yang tersisa hanya
`.py` dan `.js` polos yang dimuat browser langsung. Pustaka browser sudah divendur
di `web/lib/`, dan tidak ada langkah build.

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install "pip==24.0"                     # lihat catatan di requirements.txt
.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.12.1 torchaudio==2.11.0
.venv\Scripts\python.exe -m pip install -r requirements.txt             # jalur suara lokal
.venv\Scripts\python.exe scripts\sedia_suara.py --piper                 # voice Indonesia 61 MB
.venv\Scripts\python.exe server_py\app.py                               # satu-satunya proses yang perlu dijalankan
# buka http://127.0.0.1:8787/  (port ikut VTUBER_PORT di .env)
```

Chat tetap jalan tanpa `pip install` apa pun — hanya suaranya yang pindah ke cloud.

Sekali jalan dari nol — aset karakter tidak ikut ke git:

```bash
cp .env.example .env                    # lalu isi GEMINI_API_KEY
.venv\Scripts\python.exe scripts\unduh_aset.py      # Cubism core dari situs Live2D
# berkas ekspresi + penyihir.model3.json: buka /perkakas.html di halaman yang hidup
```

Di halaman, ketik pesannya di kolom bawah. Jalur mikrofon **sedang dimatikan** —
pipingnya masih ada (`web/mikrofon.js`, `/api/stt`, aset VAD), tinggal disambung lagi.

## Arsitektur setelah rombakan Python

Yang dulu Node sekarang Python: satu proses `server_py/app.py` memegang API key, memanggil
Gemini (chat stream / TTS / STT), menulis memori ke vault, **dan** menyajikan halaman beserta
aset model. Tidak ada bundler, tidak ada dev server terpisah.

Yang tetap JavaScript: `web/*.js`. Bukan karena pilih — Live2D hanya bisa digambar di browser,
jadi Cubism Core, Pixi, dan `pixi-live2d-display` adalah JS/WASM. Ketiganya berkas UMD siap
pakai yang dimuat dengan `<script>` biasa, sehingga tidak ada langkah build sama sekali.

| Dahulu (Node + Vite) | Sekarang |
|---|---|
| `server/index.js` | `server_py/app.py` + `gemini.py` + `memori.py` + `vault.py` |
| `npm run dev` (Vite di :5173) | `server_py/statis.py` menyajikan `web/` dan `public/` |
| `import.meta.env.VITE_*` | `window.__VTUBER_ENV__`, disuntikkan Python ke `index.html` |
| `src/*.ts` + `tsconfig.json` | `web/*.js` — ESM asli browser |
| `node_modules` (270 MB) | `web/lib/` (647 KB: pixi + cubism4 + vad) |

Sisi **chat** tetap stdlib murni: `app.py`, `gemini.py`, `memori.py`, `vault.py`,
`statis.py` tidak mengimpor satu pun paket luar. Yang butuh pip hanya **jalur suara
lokal** (`piper-tts`, `rvc-python` dan pohon dependensinya), dan impornya tertunda di
dalam fungsi — jadi venv yang belum di-`pip install` tetap menjalankan server penuh
dengan suara cloud. Parser resep wajah/pose tetap satu berkas (`web/konfigurasi.js`)
yang dipakai halaman utama DAN `/perkakas.html`; sisi Python tidak menafsirnya sama
sekali, karena dua parser berarti dua kebenaran.

## Model karakter

Karakternya model Live2D Cubism 4 (279 parameter, 617 art mesh, tekstur 8192),
dikelola di `public/models/penyihir/` dengan nama berkas dan konfigurasi bahasa Indonesia:

```
public/models/penyihir/
  penyihir.model3.json      daftar ekspresi + motion, ini yang dibaca aplikasi
  penyihir.moc3             geometri yang sudah dikompilasi (jangan disunting)
  penyihir.physics3.json    rambut, baju, perhiasan bergoyang
  penyihir.cdi3.json        label parameter untuk editor — sudah dialihbahasakan
  tekstur/texture_00.png    8192x8192
  tekstur/texture_01.png    4096x8192
  ekspresi/*.exp3.json      salinan dari resep di .env, untuk alat luar (VTube/Cubism)
  gerakan/sedih-melambai.motion3.json
```

Sembilan wajah tersusun rapi dari parameter modelnya dan dialihbahasakan ke Indonesia:
**Resepnya diatur fleksibel di `.env`** -- masing-masing adalah satu baris `VITE_WAJAH_*` /
`VITE_POSE_*` di `.env`; berkas `.exp3.json`-nya hanyalah salinan untuk perkakas luar
dan diunduh ulang dari `/perkakas.html`.
Label parameter juga tersimpan rapi di `penyihir.cdi3.json`:

| Singkatan / Parameter | Arti sebenarnya | Dipakai untuk |
|---|---|---|
| `ku` | mata berair + alis naik | `sedih` |
| `sq` | cemberut | `sebal` |
| `h` | setetes keringat + bayangan muram di mata | `bingung` |
| `xx` / `x` | pupil bintang / pupil hati | `semangat` / `goda` |
| `mz` `fz` `yj` `zs1` `zs2` `cw` `hdj` | topi, tongkat sihir, kacamata, memamerkan barang, hantu kecil, kalung | kanal `[prop:...]`, ditumpuk di atas wajah |

`netral`, `senyum`, `kaget`, dan `lelah` tidak punya lapisan sendiri di model aslinya,
jadi keempatnya saya rakit dari parameter dasar (`ParamEyeLOpen`, `ParamBrowLY`,
`ParamMouthForm`, `Param50`). Rentang tiap parameter dibaca dari model yang sedang
berjalan, bukan ditebak.

Napass, goyang kepala, dan kedip tidak butuh berkas motion — pustaka `pixi-live2d-display`
sudah menyetelnya sendiri, dan itu alasan `gerakan/` sengaja tidak dipasang sebagai Idle:
kalau ada motion yang jalan, pustaka justru mematikan kedip otomatisnya.

## Diatur lewat .env

Semua yang bergerak, berubah wajah, dan mengukur piksel dibaca dari satu berkas:
`.env` isinya, `web/konfigurasi.js` parsernya — dipakai halaman utama DAN
`web/perkakas.html`, jadi tidak bisa beda. Cara melihat apa yang sedang terpakai:
buka **`http://127.0.0.1:8787/perkakas.html`** saat server jalan.

Halaman itu menampilkan tabel wajah/pose/gerakan dari nilai efektif, peringatan
sintaks, blok `.env` siap tempel, dan tombol unduh tiap `.exp3.json` plus
`penyihir.model3.json`. Tidak ada logika kedua di dalamnya: ia mengimpor fungsi
yang sama persis dengan yang dipakai avatar. Terukur 2026-09-26: 16 dari 16 resep
dan `penyihir.model3.json` dihasilkan identik byte-per-byte dengan berkas di disk.

| Yang mau diubah | Kunci |
|---|---|
| Raut wajah (9) | `VITE_WAJAH_<NAMA>="ParamMouthForm=1 ParamEyeLOpen=-0.35"` |
| Pose / aksesoris (7) | `VITE_POSE_<NAMA>="Param72=30"`, tag `[prop:tongkat]` dan `[prop:tongkat=mati]` |
| Wajah saat dibuka dan lama pudarnya | `VITE_EKSPRESI_DASAR`, `VITE_PUDAR_WAJAH_MS` |
| Gerakan (motion) | `VITE_GERAK_<NAMA>="grup=isyarat berkas=... sumber=... ulang=false"` |
| Ukuran kotak avatar (CSS px) | `VITE_PANGGUNG_UKURAN`, `VITE_PANGGUNG_LEBAR`, `VITE_PANGGUNG_TINGGI` |
| Seberapa besar karakter mengisi kotak | `VITE_AVATAR_ZOOM`, `VITE_AVATAR_X`, `VITE_AVATAR_JANGKAR` |
| Jumlah piksel nyata / ketajaman | `VITE_RENDER_SKALA`, `VITE_RENDER_SKALA_MAKS`, `VITE_RENDER_HALUS` |
| Kedip, napas, kepala ikut kursor | `VITE_KEDIP`, `VITE_NAPAS`, `VITE_IKUTI_KURSOR` |
| Atlas tekstur yang dipasang | `VITE_TEKSTUR` (model ini sudah 8192, maksimum dari aslinya) |
| Berapa lama dia boleh menggambar (hemat GPU) | `VITE_IRAMA_JEDA_SAAT_SEMBUNYI`, `VITE_IRAMA_FPS_SAAT_TAK_FOKUS` |

Satu sintaks untuk semuanya: token `Id=Nilai` dipisah spasi; blend default `Add`
menambah di atas nilai bawaan parameter, `:Overwrite` menulis mentah, `:Multiply`
mengali; `kosong` berarti tanpa parameter. Nama kunci diterjemahkan apa adanya —
`VITE_POSE_HANTU_KECIL` menjadi pose `hantu-kecil`. Id yang tidak ada di model atau
nilai yang keluar rentang dilaporkan di status halaman ("N konfigurasi perlu dicek")
dan di log browser. Ubah nilainya cukup
muat ulang halaman; hanya berkas untuk perkakas luar yang perlu diunduh ulang
dari `/perkakas.html`.

Wajah memakai sistem ekspresi pustaka (satu wajah pada satu waktu), sedangkan pose
ditulis sebagai lapisan parameter paling akhir setiap frame — sehingga tongkat,
kacamata, atau hantu kecil tetap menempel walau wajahnya sedang sedih.

### Irama render: jangan menggambar untuk orang yang tidak melihat

Sebelum ada `web/iriama.js`, kanvas meminta frame secepat mungkin terus-menerus —
termasuk saat jendelanya tertutup jendela lain atau jadi overlay selalu-di-depan
yang sedang tidak dipandang. Pada Iris Xe itu berarti panas dan baterai. Dua knob:

| Knob | Arti | Bawaan |
|---|---|---|
| `VITE_IRAMA_JEDA_SAAT_SEMBUNYI` | `document.hidden` (tab latar, jendela diminimakan) → `ticker.stop()`: nol frame, tidak ada `requestAnimationFrame` yang tertinggal di antrean | `true` |
| `VITE_IRAMA_FPS_SAAT_TAK_FOKUS` | terlihat tapi tidak fokus → `ticker.maxFPS` dipasang ke angka ini; `0` = tidak dibatasi | `30` |

Yang **tidak** tersentuh suara: audio diputar elemen `<audio>` dan rahang dibaca
dari posisi audio itu, jadi saat halaman tersembunyi mulutnya membeku sementara
suaranya tetap jalan, dan begitu muncul lagi rahangnya langsung berada di fase yang
benar — bukan mengulang dari nol. `app.ticker` juga bukan ticker global, dan model
Live2D terdaftar di ticker itu, jadi satu `stop()` menghentikan pembaruan parameter
sekaligus penggambaran (terukur: 0 kali `internalModel.update` dalam 600 ms).

Satu temuan yang mengubah cara baca angka lama: "tab latar cuma 1 FPS" bukan
pencapaian hemat — itu Chromium yang memotong sendiri, dan dia melakukannya hanya
untuk tab. Jendela yang terlihat-tapi-tidak-fokus tetap 60 FPS, dan di mesin ini
Chrome bahkan tidak pernah melaporkan `hidden` untuk jendela yang diminimakan
(terukur `windowState=minimized`, `visibilityState=visible`, rAF tetap 60).
Jadi bagian yang benar-benar bekerja di hardware ini adalah batas 30 FPS saat tidak
fokus — itu juga yang dibutuhkan Fase 5, karena overlay selalu-di-depan tidak akan
pernah "tersembunyi".

### Kenapa avatar pernah terlihat burik saat di-zoom

Bukan tekstur: atlas model ini 8192 px, jauh di atas ukuran layar. Penyebabnya
kanvas WebGL — jumlah pikselnya ditetapkan sekali saat halaman dibuka, sementara
zoom browser mengubah `devicePixelRatio` setelahnya; browser kemudian merentangkan
gambar lama. Kini resolusinya dihitung ulang tiap rasio piksel berubah (media query
yang dipasang ulang setiap kali) dan tiap resize, jadi piksel nyata kanvas selalu
`ukuran CSS × devicePixelRatio`.

Kalau GPU mulai kalah, turunkan `VITE_RENDER_SKALA_MAKS` atau paksa satu angka lewat
`VITE_RENDER_SKALA`. Status halaman menampilkan `738×738 css · 886×886 px · 1.25×` —
kalau angka CSS dan piksel tidak sebanding, kanvas sedang diregangkan.

## Rupa panel

Rel kiri adalah dia; rel kanan adalah buku catatannya. Elaina menyendiri di jalan
dan mencatat apa yang dia lihat, dan memori build ini pun sungguh-sungguh berupa
catatan Markdown di vault — jadi panelnya sebuah ledger lapangan, bukan dashboard.

- **Warna.** Langit di atas laut awan (`#0d1119` → `#1e2739`) dengan satu aksen
  lampu minyak `#e8b673`. Amber dipakai hanya untuk yang hidup: raut aktif,
  cincin fokus, dan lampu bicara. `#c2707c` khusus galat.
- **Tipografi tanpa jaringan.** Palatino/Georgia untuk kepala, Segoe UI untuk baca,
  Cascadia/Consolas untuk angka mesin — semuanya sudah ada di Windows. Sengaja
  tidak ada tautan webfont: halaman ini harus tetap sama rupanya saat offline.
- **Lampu = `#suara`.** Titik di kanan atas menyala amber saat dia menyusun suara
  dan memerah saat TTS gugur. `chat.js` menulis teks *dan* `data-keadaan` lewat
  satu fungsi (`setSuara`) supaya keduanya tidak bisa berbeda.
- **Meteran `raut`.** Nama wajah yang sedang tampil, dibaca langsung dari
  `setEkspresi` — bukan dari tombol yang ditekan, karena wajah juga berganti lewat
  tag chat dan lewat ekspresi dasar.
- **Tidak ada animasi berulang.** Transisi 120–180ms saja, dan semuanya dimatikan
  untuk `prefers-reduced-motion`. Yang boleh bergerak terus cuma avatar-nya — dan
  `web/iriama.js` justru merampas hak itu saat dia tidak dilihat.

Desain panel responsif menjaga tata letak tetap proporsional: chip ekspresi dan kontrol
tetap rapi pada layar ringkas, indikator fokus jelas untuk keyboard accessibility,
dan kontras teks terjaga pada tema gelap.

## Cara kerja

```
papan ketik ------------------> teks --> Gemini Flash --> teks + [tag]
                                                              |
                                                        ekspresi Live2D
                     /api/tts --> jalur_suara (pekerja tunggal + cache)
                          piper     --> WAV 22,05 kHz  (offline, CPU)
                          piper+rvc --> RVC/Furina --> WAV 40 kHz
                          gemini    --> cloud, 24 kHz
                                          |
                             AnalyserNode (RMS) -> ParamMouthOpenY
```

- **`server_py/app.py`** — satu proses untuk semuanya: API key, Gemini (chat/TTS/STT),
  memori, dan sajian halaman. Hanya listen di `127.0.0.1`, membungkus PCM mentah jadi WAV,
  dan mencoba berjenjang saat model utama kena 503/429.
- **`server_py/gemini.py`** — REST Gemini lewat stdlib. `alir()` membuka koneksi SEBELUM
  mengembalikan iterator; kalau tidak, kegagalan model utama tidak tertangkap dan fallback
  cadangan tidak pernah jalan.
- **`server_py/statis.py`** — pengganti dev server: `web/` lalu `public/`, MIME benar,
  query `?import` dibuang, dan jalur di luar akar ditolak.
- **`server_py/jalur_suara.py`** — orkestrator suara: satu thread pekerja + antrean
  berbatas, cache per kalimat, dedupe pekerjaan identik, dan fallback antar-resep saat
  satu engine mati atau melewati `VTUBER_TTS_BATAS_DETIK`.
- **`server_py/tts_piper.py`** / **`tts_rvc.py`** / **`tts_gemini.py`** — satu engine per
  berkas. Ketiganya menunda impornya sendiri, jadi `import app` tidak pernah menyeret
  torch atau onnxruntime hanya untuk menjawab `/api/chat`.
- **`server_py/wav.py`** — bungkusan/baca header WAV. `sudah_wav` dipertahankan apa
  adanya: membungkus ulang WAV yang sudah lengkap itu sebab "suara hilang diam-diam".
- **`persona.md`** — sifat dan gaya bicara karakter. Ini konfigurasi, bukan model yang
  dilatih: diedit langsung, dan selalu dikirim sebagai system instruction.
- **`web/konfigurasi.js`** — parser `.env` (wajah, pose, gerakan, ukuran). Dipakai
  `index.html` dan `perkakas.html`, satu sumber kebenaran untuk dua kegunaan.
- **`web/wajah.js`** — menyuntik resep dari `.env` ke expression manager saat runtime
  dan menjaga lapisan pose tetap di atas wajah (`beforeModelUpdate`).
- **`web/ekspresi.js`** — gerbang tag: tahu nama wajah dan pose dari konfigurasi, mengenal
  kanal `[prop:...]`, dan mengupas tag itu dari layar saat teks masih mengalir.
- **`web/main.js`** — kanvas + resolusi (ikut `devicePixelRatio` terus-menerus), tombol
  panel dari `.env`, dan gerakan ulang parameter setelah motion selesai.
- **`web/mikrofon.js`** — VAD Silero di mesin ini; hanya potongan yang terdeteksi sebagai
  bicara yang dikirim untuk disalin. **Belum tersambung ke halaman** — tidak ada modul yang
  mengimpornya, jadi aset `public/vad` dan `public/ort` tidak pernah diunduh browser.
- **`web/suara.js`** — memutar WAV dan mengukur amplitudo per frame.
- **`server_py/vault.py`** — menulis/membaca catatan karakter ke vault Obsidian lewat Local
  REST API; token diambil dari `~/.qoder/settings.json`, bukan dari berkas di repo.
- **`server_py/memori.py`** — kebijakan memori: apa yang masuk prompt, bagaimana mood
  bergeser dari tag ekspresi, dan kapan fakta baru diekstrak.
- **Gerak mulut** tidak memakai penempatan fonem per kata, melainkan amplitudo
  audio yang sedang diputar, dan ditulis pada event `afterMotionUpdate` supaya
  tidak ditimpa animasi idle.

## Memori karakter

Dia tidak dilatih. Yang membuatnya terasa "ingat" adalah tiga catatan Markdown di
vault, yang dibaca ulang dan disuntikkan ke system prompt setiap kali menjawab:

```
Qoder Memory/Project/Desktop AI VTUBER/Karakter/
  Fakta.md              daftar hal yang dia ingat tentangmu
  Mood.md               valensi, energi, afinitas, jumlah pertukaran
  Riwayat/2026-09-23.md percakapan hari itu, satu baris per tukaran
```

Semuanya bisa kamu buka dan sunting langsung di Obsidian. Menghapus satu baris di
`Fakta.md` berarti dia benar-benar lupa hal itu pada balasan berikutnya.

Alur penulisannya: setiap balasan selesai → tag ekspresinya dibaca → mood bergeser
dan riwayat harian bertambah. Ekstraksi fakta memakai model dan hanya berjalan tiap
`VTUBER_JEDA_FAKTA` pertukaran, karena ia menambah satu panggilan API.

Mood bergeser dari tag yang dia pakai sendiri, tanpa panggilan tambahan: `[semangat]`
menaikkan valensi, `[sedih]` dan `[sebal]` menurunkannya, dan setiap pertukaran
menaikkan afinitas sedikit. Kalau valensinya jatuh, system prompt berikutnya berisi
"kamu lagi agak berat hari ini" — itu sebabnya nadanya berubah lintas sesi.

Kalau Obsidian sedang tidak jalan, memori dilewati dengan satu baris peringatan dan
percakapan tetap berjalan.

## Batas kuota yang nyata

Angka di bawah diukur langsung dengan kunci tingkat gratis ini, bukan asumsi.
Model mana yang "boleh" tergantung kunci: `models.list()` bisa memperlihatkan
model yang ternyata 404 saat dipakai.

| Model | Kepentingan | Terukur 2026-09-24 |
|---|---|---|
| `gemini-3.5-transcribe` | penyalin suara | **3 permintaan per menit** |
| `gemini-3.5-flash` | otak percakapan | **0/3 gagal** — 503 "high demand" |
| `gemini-3.5-flash-lite` | otak percakapan | 0/3 gagal — 503 |
| `gemini-flash-lite-latest` | otak percakapan | 1/3, dan yang lolos butuh 61 dtk |
| `gemini-2.5-flash`, `-lite` | otak percakapan | 404 — tidak dibuka untuk akun ini |
| **`gemini-3-flash-preview`** | otak percakapan | **3/3**, 3,7 / 4,2 / 21,9 dtk <- dipakai |
| `gemini-2.5-flash-preview-tts` | suara | **49-77 dtk** untuk 5 dtk audio <- ditinggalkan |
| **`gemini-3.8-flash-lite-tts`** | suara | **2,6-3,8 dtk** untuk 5 dtk audio <- dipakai |
| `gemini-3.8-flash-tts` | suara | 3,3-3,9 dtk (jadi `VTUBER_TTS_CADANGAN`) |

## Suara lokal: memasang & mengukur

Angka di bawah **terukur di mesin ini tanggal 26 September 2026** dengan
`python scripts/uji_latensi.py --resep piper+rvc --f0 pm,rmvpe --kalimat 8`.
Jangan menambahkan atau mengubah satu pun angka tanpa menjalankan ulang skripnya.

Mesin uji: i5-1135G7 (4 core/8 thread), Intel Iris Xe, 16 GB RAM, **tanpa GPU NVIDIA**.

| jalur | median per kalimat | p95 | RTF | puncak RAM |
|---|---|---|---|---|
| `piper` saja | **0,29 – 0,53 dtk** | 0,61 dtk | **0,12 – 0,19** | ±200 MB |
| `piper+rvc` f0 `pm` | 7,36 dtk (RVC-nya) | 9,93 dtk | 1,47 | 2160 MB |
| `piper+rvc` f0 `rmvpe` | 14,70 dtk (RVC-nya) | 31,51 dtk | 3,22 | 2678 MB |
| `gemini` (pembanding) | 2,6 – 3,9 dtk | — | — | — |

Kesimpulan yang diambil dari tabel itu, dan alasan `VTUBER_TTS_RANTAI` bawaannya
`piper,gemini`:

- **Piper menang telak.** Sekitar 6–9× lebih cepat dari Gemini, offline, dan tidak
  memakan kuota 20 permintaan/hari. Ini yang jadi suara utama.
- **RVC kalah gerbang.** Konversinya 7–15 dtk per kalimat, lebih lambat dari cloud
  yang mau digantikannya. Ia tetap terpasang dan bisa dipakai, tapi tidak jadi
  default — dan README ini tidak boleh menyebut "sudah lokal bersuara karakter"
  sebelum angka itu berubah.
- **Muat model RVC 7–9 dtk terjadi DI DALAM permintaan pertama** kalau
  `VTUBER_RVC_MUAT_BOOT` dibiarkan mati, sehingga kalimat pertama melewati batas
  20 dtk dan jatuh ke engine lain. Kalau menyalakan RVC, nyalakan juga knob itu.

Cara memasang (aset tidak ikut git):

```bash
.venv\Scripts\python.exe scripts/sedia_suara.py --piper        # voice id_ID, 61 MB
.venv\Scripts\python.exe scripts/sedia_suara.py --model-dasar  # hubert + rmvpe ke .venv
.venv\Scripts\python.exe scripts/sedia_suara.py --furina       # checkpoint dari E:
.venv\Scripts\python.exe scripts/sedia_suara.py --periksa      # laporan, tanpa menulis
```

`--model-dasar` perlu dijalankan ulang setiap kali `.venv` dibuat ulang: `rvc_python`
membaca `base_model/` dari dalam direktori paketnya sendiri, bukan dari proyek.

Bukti sisi browser, dijalankan 2026-09-26 pada Chromium headed (Playwright global,
bukan bagian proyek -- Node sudah tidak dipakai di sini): `POST /api/tts` membalas
`200 audio/wav` dengan `x-tts-model: piper`, `decodeAudioData` menerima berkasnya
(1,07 dtk), RMS pada `AnalyserNode` menyentuh **0,25**, dan `window.__vtuber.mulut`
bernilai **0,681** setelah `antre()` selesai. Artinya rahang benar-benar digerakkan
audio Piper, bukan hanya "file-nya valid".

Catatan metode: pemeriksaan pertama melaporkan "rahang diam" dan itu **salah tes,
salah produk** -- `antre()` tidak di-await sehingga sampel diambil sebelum konteks
audio bangun. Kalau suatu hari tes rahang melaporkan nol, curigai dulu caranya
sebelum menyalakan kodenya.

Cara memilih suara dengan telinga (angka tidak bisa mengganti ini):

```bash
.venv\Scripts\python.exe scripts/adu_suara.py --transpose 0,12
```

Rantainya dipilih lewat `.env`, tanpa menyentuh kode: `piper`, `gemini`, dan
`piper+rvc` bisa ditumpuk dengan koma, mana yang gagal dilompati. Tiga perilaku
yang membuat penumpukan itu benar-benar terpakai, bukan sekadar tertulis:

- **Hasil yang telat tetap masuk cache.** Yang menulis cache adalah pekerjanya,
  bukan penunggunya. Tanpa ini, tiap kalimat RVC yang melewati `VTUBER_TTS_BATAS_DETIK`
  dibuang hasilnya dan kalimat yang sama miss selamanya.
- **Resep yang terbukti tidak selesai diistirahatkan** selama
  `VTUBER_TTS_JEDA_RESEP` (bawaan 60 dtk). Tanpa jeda itu, kalimat ke-2..N dari satu
  jawaban panjang membayar ulang 20 dtk kegagalan yang sama -- dan kuota cloud yang
  seharusnya jadi penahan habis hanya untuk menunggu.
- **Pekerja membuang pekerjaan yang tidak ada penunggunya lagi**, dan `var/tmp-suara`
  disapu saat boot. Dua berkas `_masuk.wav` tertinggal dari proses yang dipotong di
  tengah konversi -- `finally` tidak jalan kalau prosesnya dibunuh.

Satu hal yang harus diketahui soal `piper+rvc`: voice Piper Indonesia adalah **suara berita
laki-laki berlogat asing** (MODEL CARD-nya: 1 penutur, medium, hasil fine-tune dari
suara Inggris), jadi RVC harus menjembatani gender, bukan sekadar warna — dan hasil
eksperimennya ada di halaman yang dicetak `adu_suara.py`.

## Berapa lama sampai dia bersuara

Dulu: teks 5-25 dtk (sering 503) **lalu** sintesis 49-77 dtk = belasan sampai
puluhan detik diam. Sekarang `/api/chat` mencoba `VTUBER_MODEL` lalu setiap
`VTUBER_MODEL_CADANGAN` sampai ada yang menjawab (503 itu antrean sementara dan
berbeda per model), dan setiap kalimat yang sudah selesai langsung disintesis
tanpa menunggu jawaban lengkap:

```
token pertama  --->  SUARA PERTAMA TERDENGAR     selesai
   10,0 dtk                13,3 dtk            15,1 dtk   (2 potongan)
```

Mode per kalimat itu menambah satu panggilan TTS per kalimat. Kalau kunci sering
kena batas permintaan per menit, matikan dengan `VTUBER_TTS_PER_KALIMAT=false`.
Yang masih tidak bisa dihindari di tingkat gratis adalah jeda sebelum token
pertama — itu antrean di sisi Google, dan naik ke kunci berbayar adalah satu-satunya
perbaikan yang benar-benar besar di bagian itu.

## Perkakas & Pengelolaan

```bash
.venv\Scripts\python.exe scripts/unduh_aset.py --periksa  # laporan aset: apa ada, apa hilang
.venv\Scripts\python.exe scripts/unduh_aset.py            # unduh Cubism Core dari situs Live2D
.venv\Scripts\python.exe scripts/sedia_suara.py --periksa # aset jalur suara (piper + rvc)
.venv\Scripts\python.exe scripts/uji_latensi.py           # angka latensi, bukan dugaan
.venv\Scripts\python.exe scripts/adu_suara.py             # render sampel untuk dipilih dengan telinga
```

Perkakas Python di `scripts/` membaca `.env` lewat `server_py/konfig.py` yang sama
dengan server.

Dua aset masih berstatus **tidak bisa dibangkitkan ulang** dan itu bukan hal yang
dilahirkan rombakan suara ini — lubangya sudah ada sejak `node_modules` dihapus,
cuma sebelumnya tersamar oleh skrip Node yang tampak bisa dijalankan:
`public/vad` (6,2 MB) dan `public/ort` (83 MB) di-`.gitignore` dan aslinya disalin
dari `node_modules/@ricky0123/vad-web` + `onnxruntime-web`, yang sudah tidak ada.
`scripts/unduh_aset.py --periksa` melaporkannya apa adanya. Pilihannya: keluarkan
keduanya dari `.gitignore`, atau unduh sekali paket itu lewat npm di luar proyek.
Sampai hari ini tidak mengganggu, karena jalur mikrofon memang belum punya tombol
di halaman. Berkas ekspresi dan `penyihir.model3.json` tidak lagi dibuat skrip:
unduh dari `/perkakas.html`.
Seluruh pengujian fungsional, rendering, dan integrasi telah selesai dilaksanakan dan diverifikasi.

## Kredit

Aset dan pustaka pihak ketiga yang dipakai proyek ini, beserta pemiliknya:

- **Model karakter "Penyihir"** (`public/models/penyihir`) — model Cubism 4
  dengan konfigurasi, parameter, dan ekspresi berbahasa Indonesia.
- **Live2D Cubism Core for Web** (`live2dcubismcore.min.js`) — SDK resmi
  [Live2D Inc.](https://www.live2d.com/en/sdk/download/web/), *Cubism SDK License*.
- **[pixi-live2d-display](https://github.com/guansss/pixi-live2d-display)**
  oleh guansss — MIT.
- **[PixiJS](https://github.com/pixijs/pixijs)** — MIT. Renderer WebGL.
- **[vad-web](https://github.com/ricky0123/vad)** oleh ricky0123 — MIT. Pembungkus
  deteksi bicara untuk browser.
- **[Silero VAD](https://github.com/snakers4/silero-vad)** — MIT. Model deteksi
  suara yang benar-benar berjalan di mesinmu.
- **[ONNX Runtime Web](https://github.com/microsoft/onnxruntime)** — MIT.

Gemini API dipanggil langsung lewat REST dari stdlib Python, jadi tidak ada SDK yang
ikut ke proyek. Vite, TypeScript, dan `@google/genai` dipakai pada fase awal dan sudah
dihapus bersama `node_modules`, jadi tidak lagi menjadi bagian dari daftar ini.

Kode di repositori ini adalah karya proyek; seluruh aset dan pustaka di atas
tetap pada lisensinya masing-masing.

## Lisensi

Kode sumber proyek ini bebas dipakai sesuai ketentuan yang berlaku padanya.
**Model Live2D dan Cubism Core tidak termasuk** dan tidak diizinkan untuk
diredistribusi sebagai berkas lepas — karena itu keduanya dikecualikan dari
repositori dan diambil ulang dengan `python scripts/unduh_aset.py` (Cubism Core dari
situs Live2D). Untuk karakter publik, gunakan model milik sendiri.
