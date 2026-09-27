# Rencana: Silver Wolf jadi karakter desktop (tanpa jendela)

Status: **rencana, belum ada kode baru ditulis.** Berkas ini bisa dihapus setelah
disetujui.

## Keputusan yang sudah dikunci

| Hal | Pilihan |
|---|---|
| Folder kerja | `C:\Users\Daffa\Desktop\AI VTUBER` — melanjutkan pekerjaan yang belum di-commit di sana |
| Wujud di layar | Karakter **menempel di desktop**: di belakang ikon, di bawah semua jendela, **tidak ada di taskbar maupun Alt+Tab** |
| Pemicu obrolan | **Klik kanan pada karakter** |
| Mode lama | `--browser` (panel lengkap) dan mode pet overlay yang sudah ada **tetap dipertahankan** sebagai jalur cadangan |

## Kondisi awal (terverifikasi, bukan asumsi)

- Aplikasi = satu proses Flask `main.py`; halaman `web/index.html` dua kolom
  (kanvas + rel panel). Ini yang terasa seperti "jendela Animaze".
- **Mode pet sudah jadi tapi belum di-commit** di folder Desktop:
  `server_py/jendela.py` (pywebview: frameless + transparent + on_top, dijalankan
  sebagai proses anak), `web/tampak.js` (mode `pet`, klik kanan = panel),
  `main.py --pet/--browser`, `VTUBER_TAMPAK=pet`, `pywebview` di `requirements.txt`.
  Sudah diuji: transparansi benar-benar tembus (1351/29929 titik berubah, 1445
  di antaranya kotak ujinya sendiri).
- Model `public/models/silverwolf/` ada; `.env` sudah menunjuk ke sana
  (`VITE_MODEL_URL`, RVC `SilverWolfJP`).
- `pywebview` + `pythonnet` + `clr_loader` terpasang di `.venv`; WebView2 runtime
  `153.0.4234.48` ada.
- Workspace sesi ini (`Worktrees/AI VTUBER/main-2d88f0be`) **tidak dipakai** —
  ia bersih di commit terakhir dan tidak memuat pekerjaan pet-mode.

## Tiga konsekuensi yang harus diterima lebih dulu

Ini bukan detail teknis kecil; ini yang menentukan bentuk seluruh rencana.

1. **Jendela yang ditanam ke `WorkerW` tidak bisa menerima klik.** Ia ada di
   belakang lapisan ikon desktop, jadi mouse tidak pernah sampai ke sana. Maka
   "klik kanan pada karakter" **tidak bisa** ditangani oleh halaman web — harus
   dideteksi dari luar jendela (pengintai Win32). Pilihan yang kamu ambil tetap
   bisa diwujudkan, tapi bukan dengan cara `contextmenu` di JS.
2. **Kotak obrolan tetap harus berupa jendela nyata.** Kalau ia ikut ditanam ke
   desktop, ia juga ada di bawah semua jendela dan tidak bisa diketik. Jadi saat
   dipanggil, satu kotak kecil muncul di atas. Artinya "tanpa elemen antarmuka"
   berlaku **saat diam**; saat dipanggil, wajar ada satu kotak.
3. **Karakter tidak bisa digeser dengan mouse.** Menggesernya berarti menyeret
   di atas desktop, dan desktop akan menggambar kotak seleksi ikon di belakangnya.
   Posisinya diatur dari `.env` (`VITE_AVATAR_X`, `VITE_AVATAR_ZOOM`,
   `VITE_AVATAR_JANGKAR`) — sama seperti sekarang.

## Fase 0 — HASIL (dikerjakan 27 Sep)

Probe awal mengajukan empat pertanyaan. Dua di antaranya **tidak bisa dijawab apa
adanya**, karena dua kesalahan alat ukur yang baru ketahuan saat mengerjakannya.
Yang benar-benar terukur, dan yang sudah diperbaiki:

### Alat ukur 1: BitBlt buta pada isi WebView2

Tangkapan layar lewat `BitBlt` dari screen DC **tidak bisa melihat isi WebView2**.
WebView2 menggambar lewat DirectComposition, bukan GDI; yang tertangkap cuma latar
form WinForms-nya. Inilah sebabnya seluruh percobaan pertama melaporkan "kotak
merah tidak tergambar" sementara DOM-nya jelas ada (`evaluate_js` memulangkan
`rgb(255, 0, 0)`). `PrintWindow` dengan `PW_RENDERFULLCONTENT` juga tidak menolong:
ia memaksa form melukis dirinya sendiri dan mengabaikan anak DirectComposition-nya.

Kesimpulan metodologis: **piksel karakter tidak bisa diverifikasi dari skrip.**
Yang bisa diverifikasi dari skrip hanya piksel yang dicat form (latar), dan itu
justru bagian yang bermasalah. Verifikasi visual sisanya butuh mata Master.

### Alat ukur 2: koordinat BitBlt campur satuan

`BitBlt` dari proses yang DPI-unaware memakai satuan virtual, sedangkan
`GetWindowRect` setelah `webview.start()` memulangkan satuan fisik. Layar ini
1920x1080 berskala 125%: satu tangkapan pernah diambil di (1098,41) padahal
jendelanya ada di (1372,255) -- dan hasilnya "bersih" secara menyesatkan.

### Temuan 1 — pywebview TIDAK membuat jendelanya tembus pandang

Dibaca dari sumbernya, bukan ditebak: `platforms/edgechromium.py:114` menyalakan
`DefaultBackgroundColor = Color.Transparent` pada WebView2-nya, tetapi
`platforms/winforms.py:290` hanya memanggil
`SetStyle(SupportsTransparentBackColor, True)` dan **tidak pernah** menyetel
`BackColor` beralfa maupun `TransparencyKey`. Seluruh paket pywebview 6.2.1 tidak
sekali pun memakai `TransparencyKey` atau `SetLayeredWindowAttributes`.

Terukur di jendela pet yang benar-benar jalan:
- `exstyle = 0x50008` -- **tanpa `WS_EX_LAYERED`**, jadi mustahil tembus;
- `PrintWindow` memulangkan **397.035 piksel (240,240,240) seragam** = `BackColor`
  form (`Color [Control]`) menutupi seluruh jendela.

Artinya mode pet yang ada sebelum ini menampilkan karakter di atas **kotak abu-abu
pekat**. Ini bukan risiko lagi; ini terjadi.

### Temuan 2 — jendelanya muncul di taskbar dan Alt+Tab

`WS_EX_APPWINDOW` ikut terpasang, jadi ia terasa persis seperti "jendela aplikasi"
yang justru ingin dihindari.

### Temuan 3 — dasar jendela meleset 204 px (bug DPI)

`area_kerja()` dipanggil **sebelum** `webview.start()`, saat prosesnya masih
DPI-unaware, jadi `SPI_GETWORKAREA` menjawab 1536x816 alih-alih 1920x1020. Dipakai
apa adanya, kaki karakter mendarat di y=816 -- **204 px di atas taskbar**.

### Sudah diperbaiki di `server_py/jendela.py`

| Perbaikan | Cara | Terukur sesudahnya |
|---|---|---|
| Tembus pandang | `WS_EX_LAYERED` + `SetLayeredWindowAttributes(LWA_COLORKEY)` dengan warna `BackColor` form, dibaca dari form-nya sendiri | exstyle `0x90088`; wilayah jendela di BitBlt tidak lagi (240,240,240) seragam |
| Hilang dari taskbar | `WS_EX_TOOLWINDOW` dipasang, `WS_EX_APPWINDOW` dibuang, + `SWP_FRAMECHANGED` | `WS_EX_APPWINDOW` tidak ada lagi |
| Dasar jendela | `area_kerja()` dihitung ulang **di dalam** thread `tempel_ke_dasar`, bukan diwarisi | jendela fisik `(1372,255,519,765)` -> dasar **1020**, tepat di garis taskbar |
| Judul jendela | `judul` bawaan `"Elaina"` -> `"Silver Wolf"` | sisa sebelum rename |

**Harga yang harus diketahui:** color key itu biner. Tepi karakter yang berantialias
bercampur dengan warna latar form, jadi akan ada **rim tipis sewarna latar** di
sekitar siluet. Itu batas tekniknya, bukan penyetelan yang kurang pas. Kalau rim itu
mengganggu, jalan keluarnya bukan menyetel color key melainkan mengganti rumah
render ke host beralfa sungguhan (WPF `AllowsTransparency`) -- pekerjaan terpisah.

### Yang masih perlu mata Master

Skrip tidak bisa melihat piksel karakter. Yang perlu dipastikan dengan melihat
layar: (1) tidak ada lagi kotak pekat di belakang Silver Wolf, (2) rim tepinya
seberapa terlihat, (3) karakternya sendiri tergambar utuh.


## Fase 1 — HASIL: tidak bisa di mesin ini

Diuji 27 Sep lewat `scripts/probe_tanam.py`. **Hasilnya negatif, dan bukan karena
kodenya kurang rapi.** Tiga pengukuran yang menutup jalur ini:

**1. Desktop di mesin ini tidak punya kanvas `WorkerW`.** Susunannya:

```
Progman 1536x864 (terlihat, berjudul)
  SHELLDLL_DefView 1536x864 (terlihat)
    SysListView32 1536x864 (terlihat)     <- ikon desktop
WorkerW 133x38, TIDAK terlihat  (x15, semuanya kosong)
```

`SHELLDLL_DefView` menempel di `Progman`, bukan di `WorkerW` — ini varian yang
memang ada di sebagian versi Windows. Lima belas `WorkerW` yang ada semuanya
133x38 dan tak terlihat, jadi bukan kanvas (sebagian adalah sampah dari percobaan
saya sendiri yang memanggil `0x052C` berkali-kali).

**2. Progman tidak mau melahirkan kanvas itu.** Pesan `0x052C` dicoba dengan empat
variasi parameter — `(wParam,lParam)` = `(0,0)`, `(0x0D,0x01)`, `(0x0D,0x00)`,
`(0,1)` — dan **tidak satu pun** menghasilkan `WorkerW` selebar layar yang terlihat.
Teknik yang jadi dasar semua aplikasi wallpaper hidup itu tidak tersedia di sini.

**3. Memaksa tanam justru mematikan renderer.** `SetParent` biasa ditolak (gaya
jendelanya bukan `WS_CHILD`). Setelah `WS_CHILD` dipasang paksa, `SetParent` ke
`Progman` **berhasil** — induknya benar-benar berubah — tetapi jendelanya langsung
**runtuh jadi 0x0, `IsWindowVisible` jadi False, dan pohon jendela kehilangan
permukaan WebView2-nya** (`Chrome_WidgetWin_0` hilang). Jadi karakternya bukan
cuma pindah tempat; ia berhenti tergambar.

Satu jalur masih tersisa secara teori: **membuat jendela sebagai anak `Progman`
sejak lahir**, bukan ditanam belakangan. pywebview tidak bisa itu; perlu host
sendiri (pythonnet + WinForms + WebView2) yang memasang `Parent` sebelum jendelanya
ditampilkan. Itu pekerjaan tersendiri, dan **belum terbukti** — bahkan kalau jadi,
ongkosnya tetap sama: tidak bisa diklik, dan hilang setiap Explorer restart.

**Kesimpulan.** "Karakter jadi bagian desktop, di belakang ikon" **tidak bisa
diwujudkan di mesin ini** dengan renderer sekarang. Yang bisa diwujudkan, dan sudah
dikerjakan, adalah bentuk yang paling dekat dengannya: jendela tanpa bingkai,
tembus pandang, tanpa taskbar, karakter melayang di desktop — lihat Fase 0.

## Fase 2 — Kotak pukul karakter (hit-test)

Klik kanan harus dijawab "apakah kursor sedang di atas karakter?", dan jawabannya
tidak boleh berupa kotak tebak-tebakan di `.env`.

- `web/main.js`: setelah `layout()`, ambil `model.getBounds()` (sudah tersedia di
  Pixi), kirim ke server lewat `POST /api/pet/rect`.
- `main.py`: rute baru `POST /api/pet/rect` (simpan di memori) dan
  `GET /api/pet/rect` (baca). Tidak menulis berkas, tidak ada format kedua.
- Pengintai di proses GUI membaca `GET /api/pet/rect` tiap 1 dtk.

Catatan jujur: `getBounds()` memulangkan kotak pembatas sprite, jadi ia termasuk
piksel transparan di sekeliling rambut dan tangan. Kotak pukulnya akan sedikit
lebih longgar dari siluet. Itu bisa diterima; kalau nanti terasa mengganggu,
batasnya bisa diperketat dengan membaca alpha dari kanvas.

## Fase 3 — Pengintai klik kanan + kotak obrolan

Di proses GUI (`jendela.py`), thread daemon:

```
tiap 30 ms:
  kalau GetAsyncKeyState(VK_RBUTTON) baru turun:
      pt = GetCursorPos()
      kalau pt di dalam rect karakter
         dan WindowFromPoint(pt) adalah desktop (bukan jendela lain):
            buka kotak obrolan di dekat pt
      tunggu sampai tombol dilepas   # supaya tidak memicu berulang
```

`GetAsyncKeyState` bekerja global tanpa peduli jendela mana yang fokus, jadi ini
tidak perlu hook keyboard/mouse sama sekali — dan itu penting: `WH_MOUSE_LL` yang
lambat akan dibuang sendiri oleh Windows, sedangkan polling 30 ms hanya dua
panggilan API yang murah.

Pemeriksaan `WindowFromPoint` wajib: tanpa itu, klik kanan di atas jendela lain
yang kebetulan menutupi karakter akan ikut memicu.

Kotak obrolan = jendela kedua dari proses GUI yang sama:

- `webview.create_window(..., url=base + "/?tampak=obrolan", frameless=True,
  on_top=True, hidden=True)`; muncul saat dipicu, `window.move()` ke dekat kursor,
  sembunyi saat `Esc` / kehilangan fokus / klik di luar.
- `web/tampak.js`: tambah mode `obrolan` — sembunyikan kanvas dan segalanya
  kecuali `#log`, `#form`, dan lampu `#suara`.
- `web/main.js`: jangan jalankan `boot()` (model Live2D) di mode `obrolan`; jendela
  ini tidak perlu kanvas dan tidak perlu memuat model 4 MB.

Satu halaman, empat wujud (`browser` / `pet` / `desktop` / `obrolan`) — sengaja,
supaya kontrak DOM yang dipakai `chat.js` tidak bercabang jadi dua sumber
kebenaran, sama seperti keputusan yang sudah ada di `web/tampak.js`.

## Fase 4 — Perkakas dan konfigurasi

- `.env` + `.env.example`: `VTUBER_TAMPAK=desktop`, dan knob kotak pukul
  (`VTUBER_PET_LEGA_PIKSEL` untuk menambah/mengurangi kelonggaran rect).
- `main.py`: `--desktop` (bawaan baru), `--pet` (overlay lama), `--browser`.
- `jalankan.bat`: bunyi pesannya disesuaikan ("klik kanan pada dia untuk membuka
  kotak chat").
- `README.md`: bagian baru yang menyebut keempat wujud, cara mengembalikan ke
  mode lama, dan konsekuensi 1–3 di atas.

## Berkas yang disentuh

| Berkas | Perubahan | Status |
|---|---|---|
| `server_py/jendela.py` | `tembuskan()` (layered + color key + buang dari taskbar), `tempel_ke_dasar()` hitung ulang area kerja, judul `Silver Wolf` | **sudah** |
| `server_py/jendela.py` | mode `desktop`: tanam ke WorkerW, penjaga Explorer, pengintai klik kanan, jendela obrolan | belum |
| `main.py` | `--desktop`, rute `POST`/`GET /api/pet/rect` | belum |
| `web/tampak.js` | mode `obrolan`; mode `desktop` = tanpa panel sama sekali | belum |
| `web/index.html` | CSS `html[data-tampak="desktop"]` dan `="obrolan"` | belum |
| `web/main.js` | kirim `getBounds()` ke server; jangan `boot()` di mode `obrolan` | belum |
| `.env`, `.env.example`, `jalankan.bat`, `README.md` | knob + dokumentasi | belum |
| `scripts/probe_desktop.py`, `scripts/probe_lihat.py` | perkakas ukur, ditinggalkan | **sudah** |

Yang **tidak** disentuh: seluruh jalur LLM/TTS/STT/memori, `persona.md`,
`web/chat.js`, `web/suara.js`, `web/mikrofon.js`. Karakter yang sama, suara yang
sama — yang berubah hanya di mana ia digambar dan bagaimana obrolan dipanggil.

## Cara menguji (kriteria lulus)

1. `jalankan.bat` → tidak ada entri di taskbar, tidak ada di Alt+Tab.
2. Ikon desktop terlihat **di atas** karakter; membuka jendela apa pun menutupi dia.
3. Wallpaper di sekeliling karakter utuh — tidak ada kotak pekat.
4. Klik kanan tepat di karakter → kotak chat muncul; klik kanan di tempat lain →
   tidak terjadi apa-apa; klik kanan di atas jendela lain yang menutupi karakter →
   tidak terjadi apa-apa.
5. Kirim satu pesan → wajah, suara, dan gerak rahang jalan seperti mode browser.
6. `Esc` menutup kotak chat; karakter tetap di tempatnya.
7. Restart `explorer.exe` dari Task Manager → karakter kembali dalam ~2 dtk.
8. `python main.py --browser` masih memberi panel lengkap seperti sebelumnya.

## Risiko, berurutan dari yang paling mungkin

1. ~~Transparansi hilang setelah `SetParent`~~ → **sudah terjadi lebih awal dari
   dugaan** (jendelanya memang tidak pernah tembus, bahkan sebelum ditanam) dan
   sudah diperbaiki lewat color key. Risiko yang tersisa tinggal rim tepinya.
2. **Isi WebView2 tidak bisa diverifikasi dari skrip.** Ini risiko yang paling
   mengganggu sekarang: setiap perubahan yang menyentuh tampilan hanya bisa
   diperiksa oleh mata Master. Jangan percaya laporan "sudah jalan" dari skrip
   untuk apa pun yang menyangkut piksel karakter.
3. **WebView2 pernah tidak lahir sama sekali** saat `storage_path` dipakai: pohon
   jendela cuma berisi form, `BrowserProcessId` tetap `None`, tanpa galat apa pun.
   Persis regresi sunyi yang sudah dicatat di `jendela.py`. Karena itu
   `storage_path` tidak dipakai, dan setiap jendela harus dibuat dalam keadaan
   TAMPIL -- `hidden=True` juga mematikan WebView2-nya diam-diam.
4. **Transparansi setelah ditanam ke `WorkerW` belum diuji.** Color key bekerja di
   jendela biasa; apakah ia bertahan setelah `SetParent` belum dibuktikan.
5. `window.show()`/`move()` dari thread pengintai sementara `webview.start()`
   memegang loop pesan. Kalau pywebview menolak, pengintai dipindah ke dalam
   callback `webview.start(fungsi)`.
6. Multi-monitor: `WorkerW` ada per monitor; versi ini hanya monitor utama.
7. Game fullscreen eksklusif: lapisan desktop tidak terpengaruh — justru ini
   keunggulan dibanding overlay `on_top`, yang biasanya ikut tersembunyi.

## Urutan kerja

Fase 0 **selesai**: dua hal yang dianggap risiko ternyata sudah terjadi (jendela
pekat, muncul di taskbar), satu bug DPI ikut ketahuan, ketiganya sudah diperbaiki
dan terukur di `server_py/jendela.py`.

Fase 1 **selesai dengan hasil negatif**: menanam karakter ke lapisan desktop tidak
bisa di mesin ini (lihat bagiannya). Karena Fase 2 dan 3 berdiri di atas penanaman
itu — kotak pukul dan pengintai klik kanan hanya ada gunanya kalau karakternya
sudah menyatu dengan desktop — **keduanya ikut gugur**, bukan ditunda.

Yang tersisa dan masih masuk akal:

1. **Master melihat layarnya**: kotak pekat sudah hilang, rim tepi seberapa
   terlihat, karakter tergambar utuh. Ini satu-satunya bagian yang tidak bisa
   diukur skrip.
2. Kalau rim terlalu mengganggu → putuskan: terima, atau ganti rumah render ke
   host beralfa sungguhan (pekerjaan terpisah, bukan penyetelan).
3. ~~Kalau ternyata masih ingin "terasa seperti bukan jendela", yang bisa dikerjakan
   tanpa menanam: sembunyikan diri, ikon tray, dan hotkey global.~~ **SUDAH
   DIKERJAKAN** — Master memilih jalur ini. Rinciannya di bawah.
4. Jalur yang benar-benar menyatu dengan desktop hanya tersisa satu: host sendiri
   (pythonnet + WinForms + WebView2) yang lahir sebagai anak `Progman`. Belum
   terbukti, dan ongkosnya tetap: tidak bisa diklik, hilang saat Explorer restart.

Perkakas ukur yang ditinggalkan: `scripts/probe_desktop.py` (helper tangkap/ukur),
`scripts/probe_lihat.py` (tangka satu wilayah atau satu jendela ke PNG), dan
`scripts/probe_tanam.py` (uji tanam, lengkap dengan hasil negatifnya supaya tidak
diulang dari nol).

## Fase 5 — Perilaku "biar tidak terasa seperti jendela" (dikerjakan)

Dipilih Master sebagai ganti Fase 1–3. Yang dibangun:

| Bagian | Di mana | Knob |
|---|---|---|
| Sembunyi otomatis | `jendela.pantau()` | `VTUBER_PET_SEMBUNYI` = `layar-penuh` \| `maksimal` \| `tidak` |
| Ikon tray | `jendela.pasang_tray()` | `VTUBER_PET_TRAY` |
| Hotkey kotak obrolan | `jendela.pantau()` + `window.__vtuberPanel()` | `VTUBER_PET_HOTKEY` |

Keputusan yang perlu diketahui:

- **Aturan bawaannya `layar-penuh`, bukan `maksimal`.** Jendela maksimal adalah
  keadaan kerja sehari-hari di mesin ini, jadi aturan `maksimal` akan menyembunyikan
  karakternya hampir sepanjang waktu. `layar-penuh` hanya bereaksi pada video layar
  penuh dan game — persis saat overlay benar-benar mengganggu.
- **Hotkey wajib punya penahan.** `hotkey_vk("s")` memulangkan `None`; tanpa syarat
  itu, mengetik huruf `s` di aplikasi mana pun akan membuka kotak obrolan.
- **Kehendak manual dari tray menang** atas aturan otomatis, dan dilepas begitu
  keadaan layar penuh berubah — supaya karakternya tidak bisa terjebak sembunyi.
- **Klik kanan dan hotkey lewat satu pintu** (`window.__vtuberPanel`), bukan dua
  jalur yang menulis keadaan yang sama.

Yang **belum** bisa diverifikasi skrip: apakah isi karakter tetap tergambar setelah
`sembunyikan`/`tampilkan`. Yang terukur cuma strukturnya — `IsWindowVisible` berubah
benar (True → False → True), dan pohon jendela serta rect-nya utuh sesudahnya. Sisa
verifikasinya mata Master.

Dua jebakan pythonnet yang sudah dibayar, jangan diulang:
`ToolStripMenuItem(str, None, EventHandler)` tidak bisa diselesaikan ("No method
matches given arguments") — item dibuat lewat teksnya saja lalu `Click +=
EventHandler(...)`; dan `import clr` + `AddReference` dilakukan DI DALAM thread tray,
bukan di thread utama sebelum `webview.start()`, supaya WinForms tidak memuat lebih
dulu dan ikut menyetel DPI awareness.
