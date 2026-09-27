# AI VTuber

Teman desktop berbasis Live2D yang bisa diajak ngobrol lewat teks maupun suara,
menjawab dengan suara, dan menggerakkan wajah serta rahang sesuai isi pembicaraannya.

Status: renderer Live2D, loop chat lokal (Llama 3.2 3B GGUF di CPU **atau** GPU
terintegrasi), ekspresi, text-to-speech lokal (Piper + RVC Furina), **mic lokal
(Whisper)**, dan memori jangka panjang Obsidian sudah berjalan.

**100% offline.** Chat, suara, dan mic dihitung di mesin ini; tidak ada satu pun
jalur runtime yang membuka koneksi ke luar. Yang masih butuh internet hanya
mendatangkan aset/binary ke mesin ini (lihat "Aset" di bawah) -- dan setelah itu ada
di disk, server tidak pernah memanggilnya lagi.

## Menjalankan

Prasyarat: **Python 3.10**. Tidak ada Node lagi di proyek ini — yang tersisa hanya
`.py` dan `.js` polos yang dimuat browser langsung. Pustaka browser sudah divendur
di `web/lib/`, dan tidak ada langkah build.

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install "pip==24.0"                     # lihat catatan di requirements.txt
.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.12.1 torchaudio==2.11.0
.venv\Scripts\python.exe -m pip install -r requirements.txt             # jalur LLM lokal + suara + mic
cp .env.example .env                    # sesuaikan konfigurasi jika diperlukan
.venv\Scripts\python.exe main.py        # satu-satunya proses yang perlu dijalankan
# buka http://127.0.0.1:8787/  (port ikut VTUBER_PORT di .env)
```

Atau dua kali klik: `jalankan.bat`.

Kalau `bin/llama/` kosong, `VTUBER_LLM_PROVIDER=vulkan` jatuh ke CPU dan **mengatakannya**
di baris banner -- lihat "GPU terintegrasi" sebelum menyalakan jalur itu. Tanpa
`pip install`, tidak ada engine yang bisa jalan: `/api/chat` membalas 503 dan `/api/tts`
menyerah dengan pesan jelas. **Tidak ada satu pun jalur yang jatuh ke cloud.**

## Aset

Proyek ini **tidak lagi membawa skrip pengunduh**. Semua aset di bawah sudah ada di
mesin ini dan di-`.gitignore` (lisensi Live2D melarang modelnya diedarkan sebagai
berkas lepas, dan yang lain terlalu besar untuk repo). Kalau pindah mesin atau
`.venv` dibuat ulang, aset-aset ini **disalin manual** -- tidak ada lagi tombolnya:

| Lokasi | Isi | Cara mendapatkannya dulu |
|---|---|---|
| `model/*.gguf` | Llama 3.2 3B Q4_K_M (2,02 GB) | GGUF Llama 3.2 dari HuggingFace |
| `aset/suara/piper/` | voice Indonesia `id_ID-news_tts-medium` (61 MB) | rilis Piper |
| `aset/suara/rvc/` | checkpoint Furina (v2, 40 kHz) | hasil latih di Applio |
| `aset/suara/model-dasar/` | HuBERT + rmvpe (±730 MB) | unduhan dasar `rvc_python` |
| `aset/suara/whisper/` | `base` (142 MB) / `small` (470 MB) | repo `Systran/faster-whisper-*` |
| `bin/llama/` | `llama-server.exe` + DLL Vulkan (92 MB) | build Windows resmi llama.cpp |
| `public/models/penyihir/` | model karakter + tekstur 8192 | berkas kerja karakter |
| `public/live2dcubismcore.min.js` | Cubism Core | SDK resmi Live2D |

Dua catatan yang masih benar: `base_model/` RVC hidup **di dalam**
`.venv/Lib/site-packages/rvc_python/`, jadi `.venv` baru berarti menyalin ulang
±730 MB itu ke sana. Dan berkas ekspresi + `penyihir.model3.json` dibuat lewat
halaman **`/perkakas.html`** di browser, bukan skrip.

## Arsitektur Full Offline

Yang dulu Node sekarang Python: satu proses `main.py` (Flask) menjalankan model lokal (Llama 3.2 GGUF via `llama-cpp-python`),
sintesis suara lokal (Piper + RVC Furina), menulis memori ke vault Obsidian, **dan** menyajikan halaman beserta
aset model. 100% offline tanpa dev server terpisah.

| Komponen | Dahulu (Node + Vite) | Sekarang (Python 100% Offline) |
|---|---|---|
| **Server & LLM** | `server/index.js` (Cloud Gemini API) | `main.py` (Flask) + `model_lokal.py` (CPU) / `model_vulkan.py` (GPU terintegrasi) |
| **Mic (STT)** | Web Speech API browser (cloud Google) | `web/mikrofon.js` rekam WAV -> `server_py/stt_whisper.py` (Whisper lokal) |
| **Penyaji Web** | `npm run dev` (Vite di :5173) | `server_py/statis.py` menyajikan `web/` dan `public/` |
| **Env Web** | `import.meta.env.VITE_*` | `window.__VTUBER_ENV__`, disuntikkan Python ke `index.html` |
| **Frontend** | `src/*.ts` + `tsconfig.json` | `web/*.js` — ESM asli browser tanpa build step |
| **Pustaka Web** | `node_modules` (270 MB) | `web/lib/` (647 KB: pixi + cubism4 + vad) |

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
papan ketik ---------------> teks --> Llama 3.2 3B GGUF --> teks + [tag]
                                       (CPU / Vulkan GPU)        |
mic --> WAV 16 kHz --> /api/stt --> Whisper base --> teks         |
           (lokal, di mesin ini)                                  |
                                                            ekspresi Live2D
                     /api/tts --> jalur_suara (pekerja tunggal + cache)
                          piper     --> WAV 22,05 kHz  (offline, CPU)
                          piper+rvc --> RVC/Furina --> WAV 40 kHz
                                          |
                             AnalyserNode (RMS) -> ParamMouthOpenY
```

- **`main.py`** — satu proses untuk semuanya (Flask): LLM lokal (`model_lokal` / `model_vulkan`), TTS lokal (`jalur_suara`),
  memori Obsidian (`vault`), dan sajian halaman (`statis`).
- **`server_py/model_lokal.py`** — streaming inferensi LLM offline menggunakan `llama-cpp-python` membaca GGUF di `model/`.
- **`server_py/model_vulkan.py`** — penyedia chat di GPU terintegrasi: menyalakan
  `bin/llama/llama-server.exe` sebagai **proses anak** (port acak, hanya 127.0.0.1,
  API key acak per boot), streaming dari `/v1/chat/completions`, dan menyapu sisa
  proses lama saat boot. Bentuk keluarannya sama dengan `model_lokal.alir()`, jadi
  sisi streaming `main.py` tidak perlu tahu mana yang menjawab.
- **`server_py/stt_whisper.py`** — mic jadi teks: WAV dari browser -> `wave` (stdlib)
  -> numpy -> faster-whisper (CTranslate2, CPU, `int8`). Model dibuka dari folder
  dengan jalur lengkap, tanpa `download_root`, tanpa HuggingFace hub.
- **`server_py/statis.py`** — pengganti dev server: menyajikan `web/` dan `public/`, MIME presisi, dan perlindungan path traversal.
- **`server_py/jalur_suara.py`** — orkestrator suara: satu thread pekerja + antrean berbatas, cache per kalimat, dedupe pekerjaan identik, dan fallback antar-resep saat satu engine melewati batas waktu.
- **`server_py/tts_piper.py`** / **`tts_rvc.py`** — engine TTS lokal: Piper ONNX dan RVC Voice Conversion Furina.
- **`server_py/wav.py`** — bungkusan dan pembaca header WAV.
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
- **`web/mikrofon.js`** — tombol mic di halaman chat. **Tidak ada lagi Web Speech API**:
  browser merekam lewat `getUserMedia` + `ScriptProcessor`, memotong pada jeda diam
  (ambang RMS 0,012, sama dengan lantai noise lip-sync), membungkus WAV 16 kHz mono,
  dan mengirimnya ke `/api/stt`. Semuanya terjadi di dalam mesin.
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

## Suara lokal: performa & benchmark offline

Angka di bawah **terukur di mesin ini** pada 26 Sep (rantai penuh, 8 kalimat, dua f0).
Mesin uji: i5-1135G7 (4 core/8 thread), Intel Iris Xe, 16 GB RAM, **tanpa GPU NVIDIA**.

| Jalur / Engine | Median per kalimat | p95 | RTF | Puncak RAM | Keterangan |
|---|---|---|---|---|---|
| `piper` saja | **0,29 – 0,53 dtk** | 0,61 dtk | **0,12 – 0,19** | ±200 MB | Sangat cepat, real-time |
| `piper+rvc` f0 `pm` | 7,36 dtk | 9,93 dtk | 1,47 | 2160 MB | Default cepat CPU |
| `piper+rvc` f0 `rmvpe` | 8,04 dtk | 14,70 dtk | 1,80 | 2678 MB | Nada lebih halus |

Kesimpulan performa:
- **Piper TTS** menghasilkan audio dalam pecahan detik (<0.5s), sangat efisien di CPU.
- **RVC** memberikan pewarnaan suara Furina yang khas.
- **Cache suara otomatis** instan (<5ms) untuk kalimat yang pernah disintesis sebelumnya.
- Rantainya dipilih lewat `.env`: `VTUBER_TTS_RANTAI=piper+rvc,piper`. Jika RVC sibuk atau melewati batas detik, sistem otomatis fallback ke Piper murni.

Cara memasang: lihat tabel **Aset** -- semuanya disalin manual ke tempatnya.

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

Rantainya dipilih lewat `.env`, tanpa menyentuh kode: `piper` dan `piper+rvc` bisa ditumpuk dengan koma, mana yang gagal dilompati. Tiga perilaku
yang membuat penumpukan itu benar-benar terpakai, bukan sekadar tertulis:

- **Hasil yang telat tetap masuk cache.** Yang menulis cache adalah pekerjanya,
  bukan penunggunya. Tanpa ini, tiap kalimat RVC yang melewati `VTUBER_TTS_BATAS_DETIK`
  dibuang hasilnya dan kalimat yang sama miss selamanya.
- **Resep yang terbukti tidak selesai diistirahatkan** selama
  `VTUBER_TTS_JEDA_RESEP` (bawaan 60 dtk). Tanpa jeda itu, kalimat ke-2..N dari satu
  jawaban panjang membayar ulang 20 dtk kegagalan yang sama -- dan yang habis bukan
  kuota, tapi CPU mesin ini sendiri.
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

Mode per kalimat itu menambah satu panggilan TTS per kalimat. Biayanya nyata di CPU
ini (Piper 0,3-0,5 dtk, `piper+rvc` 7-15 dtk per kalimat), jadi matikan dengan
`VTUBER_TTS_PER_KALIMAT=false` kalau suara mulai tertinggal dari teks. Jeda sebelum
token pertama bukan lagi antrean di sisi Google seperti dulu: itu prompt-processing
Llama 3.2 di mesin ini sendiri, dan dua perbaikan yang benar-benar terbukti ada di
bagian "GPU terintegrasi" — memindahkan hitungan ke Iris Xe (110 -> 171 tok/dtk) dan
menyimpan persona di prompt cache (4,6 dtk -> 0,4 dtk pada slot hangat).

## GPU terintegrasi: apa yang benar-benar bisa dipindahkan

Mesin ukur: i5-1135G7 + **Intel Iris Xe**, 16 GB RAM, tanpa GPU diskret, driver
32.0.101.7088, Vulkan 1.4.

Yang harus diterima lebih dulu: **Iris Xe tidak punya VRAM sendiri.** Angka
"Shared GPU memory 7,9 GB" di Task Manager dipinjam dari 16 GB RAM yang sama dengan
yang dipakai model. Jadi memindahkan kerja ke GPU di sini menambah **daya hitung**,
bukan menambah memori — dan kalau yang habis adalah RAM, GPU tidak menolong.

`llama-bench` resmi, Llama 3.2 3B Q4_K_M, prompt 2048 token + generate 128 token,
3 pengulangan, flash attention menyala:

| penempatan lapis | baca prompt (tok/dtk) | keluar token (tok/dtk) |
|---|---|---|
| `-ngl 0` (CPU murni) | 109,7 ± 10,4 | 5,05 ± 1,11 |
| `-ngl 99` (Vulkan penuh) | **171,1 ± 8,0** | **9,91 ± 0,11** |

Dua hal yang tidak terlihat dari satu angka:

1. **`-fa on` adalah syarat, bukan hiasan.** Pengukuran pertama tanpa flash attention
   justru membalik keadaannya (GPU 6,8 vs CPU 8,6 tok/dtk) dan hampir membuat jalur
   ini dibuang. Dengan flash attention menyala, GPU menang di kedua kolom — dan
   keluar token jauh lebih **stabil** (±0,11 vs ±1,11), yang terasa sebagai suara yang
   tidak tersendat.
2. **Lebih sedikit lapis GPU bukan kompromi yang aman.** Sapuan `-ngl 0,8,16,24,99`
   memberi 138 / 141 / 156 / 163 / 166 tok/dtk untuk prompt, tapi keluar token di
   `-ngl 16` jatuh ke 6,9. Campuran CPU+GPU membayar sinkronisasi di tiap batas lapis.

Terukur di aplikasi nyata (`/api/chat`, satu proses `main.py`): byte pertama **4,6 dtk**
pada giliran pertama, lalu **0,4 dtk** saat slotnya masih hangat (`--cache-idle-slots`
menyimpan persona panjang di prompt cache, jadi tidak dihitung ulang tiap giliran).

**Yang TIDAK bisa dan tidak akan pernah bisa pindah ke GPU di proyek ini:** RVC.
Konversinya PyTorch, dan `torch-directml` tidak punya wheel untuk kombinasi
torch 2.12 + Python 3.10 di mesin ini (dicek langsung: `No matching distribution
found`). Jadi `piper+rvc` tetap CPU 7-15 dtk per kalimat, dan itu batas mesin, bukan
kelalaian konfigurasi. Piper juga sengaja dibiarkan di CPU: 0,3-0,5 dtk per kalimat
sudah cukup cepat, dan menggantinya berarti menukar `onnxruntime` yang sekarang
memegang seluruh jalur suara.

## Mic lokal: angka dan buktinya

`whisper/base` int8, 2 thread CPU, ucapan 7,8 detik hasil Piper:

| keadaan | waktu |
|---|---|
| panggilan pertama (model baru dimuat) | 1,5 dtk |
| panggilan berikutnya | **0,77 dtk** |
| hasil salin | `Apa yang bisa saya bantu hari ini?` |

`small` (470 MB) tersedia lewat `VTUBER_STT_MODEL=small` kalau akurasi `base` kurang;
di CPU ini `medium` tidak dicoba karena RAM kosong tinggal ±4,5 GB saat browser dan
llama-server sudah hidup.

Jalur utuhnya dibuktikan di browser nyata, bukan hanya di ujung server: Chromium
dengan mikrofon palsu (`--use-fake-file-for-audio-capture`) berisi WAV Piper, klik
tombol mic, dan hasilnya masuk ke log chat lalu dijawab Elaina. Satu catatan untuk
yang menulis ulang tes ini: Chrome **tidak** mengalirkan audio file-palsu pada sesi
`getUserMedia` pertama (terukur: 0 blok audio), jadi tes perlu membuka perangkat
sekali sebagai pemanasan sebelum klik. Itu kelakuan alat uji, bukan produk.

## Perkakas & Pengelolaan

```bash
.venv\Scripts\python.exe scripts/adu_suara.py   # render sampel suara untuk dipilih dengan telinga
```

Satu-satunya perkakas yang tersisa di `scripts/` itu membaca `.env` lewat
`server_py/konfig.py` yang sama dengan server, dan `update_waifu_memory.py`
(penjaga pulau memori karakter -- bukan perkakas teknis).

Yang **tidak ada lagi**: pengunduh aset (`unduh_*`, `sedia_*`) dan seluruh suiter
tes (`uji_jalan`, `uji_suara`, `uji_kontrak` + `kontrak.json`). Itu pilihan pada
27 Sep, dan konsekuensinya perlu disebut jujur: tidak ada lagi yang otomatis
menangkap kalau suatu hari ada kode yang diam-diam memanggil cloud, dan tidak ada
lagi yang membuktikan kontrak HTTP `/api/*` tidak berubah bentuk. Yang masih
menjaga adalah baris banner saat boot (ia menyebut engine yang benar-benar hidup
atau mengakuinya mati) dan pesan 503 dari tiap endpoint.

`public/vad` (6,2 MB) dan `public/ort` (83 MB) sampai sekarang tidak dipakai siapa-siapa:
mic memakai ambang RMS sendiri, bukan Silero VAD. Keduanya tinggal menunggu untuk dihapus.

## Kredit

Aset dan pustaka pihak ketiga yang dipakai proyek ini, beserta pemiliknya:

- **Model karakter "Penyihir"** (`public/models/penyihir`) — model Cubism 4
  dengan konfigurasi, parameter, dan ekspresi berbahasa Indonesia.
- **Live2D Cubism Core for Web** (`live2dcubismcore.min.js`) — SDK resmi
  [Live2D Inc.](https://www.live2d.com/en/sdk/download/web/), *Cubism SDK License*.
- **[pixi-live2d-display](https://github.com/guansss/pixi-live2d-display)**
  oleh guansss — MIT.
- **[PixiJS](https://github.com/pixijs/pixijs)** — MIT. Renderer WebGL.
- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** oleh ggml-org — MIT.
  `llama-server` + backend Vulkan yang menghitung Llama 3.2 di Iris Xe; biner
  Windows resminya disalin sekali ke `bin/llama/` (versi dipaku
  `b11206`, karena angka 171 tok/dtk adalah angka build itu).
- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** oleh SYSTRAN — MIT,
  di atas **[CTranslate2](https://github.com/OpenNMT/CTranslate2)** (MIT).
- **[Whisper](https://github.com/openai/whisper)** oleh Open — MIT. Model `base`/`small`
  bahasa Indonesia yang menyalin mic di mesin ini.
- **[Piper](https://github.com/rhasspy/piper)** — MIT. TTS Indonesia (voice
  `id_ID-news_tts-medium`, satu penutur, kualitas medium).
- **[RVC](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)** via
  fork `rvc_python` — MIT. Konversi warna suara ke Furina.
- **[vad-web](https://github.com/ricky0123/vad)** oleh ricky0123 — MIT. Pembungkus
  deteksi bicara untuk browser. **Status sekarang: tidak dipakai** — `mikrofon.js`
  memakai ambang RMS sendiri, jadi `public/vad` + `public/ort` (±89 MB) hanya sisa.
- **[Silero VAD](https://github.com/snakers4/silero-vad)** — MIT. Model deteksi
  suara; sama: tersedia di disk, belum tersambung.
- **[ONNX Runtime Web](https://github.com/microsoft/onnxruntime)** — MIT.

Sistem berjalan 100% offline: chat, suara, dan mic dihitung di CPU/GPU lokal tanpa
satu pun panggilan cloud. Vite,
TypeScript, dan `@google/genai` dipakai pada fase awal dan sudah dihapus bersama
`node_modules`; Web Speech API (mic ke server Google) menyusul pada 27 Sep.

Kode di repositori ini adalah karya proyek; seluruh aset dan pustaka di atas
tetap pada lisensinya masing-masing.

## Lisensi

Kode sumber proyek ini bebas dipakai sesuai ketentuan yang berlaku padanya.
**Model Live2D dan Cubism Core tidak termasuk** dan tidak diizinkan untuk
diredistribusi sebagai berkas lepas — karena itu keduanya dikecualikan dari
repositori (lihat tabel **Aset**). Cubism Core diambil dari situs resmi Live2D.
Untuk karakter publik, gunakan model milik sendiri.
