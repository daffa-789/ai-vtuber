/**
 * Jalur mikrofon (Speech-to-Text) -- 100% lokal.
 *
 * Dulu berkas ini memakai Web Speech API bawaan browser. Itu BUKAN offline: di
 * Chrome/Edge audio mic dikompresi dan dikirim ke server Google/Microsoft
 * untuk ditranskrip, jadi percakapan yang mengaku "tanpa cloud" sebenarnya masih
 * mengirim suara Master keluar mesin.
 *
 * Sekarang: browser hanya merekam, memotong pada jeda diam, dan mengirim WAV 16 kHz
 * mono ke /api/stt. Transkripsinya dibuat oleh Whisper di mesin ini (stt_whisper.py).
 * Tidak ada pustaka pihak ketiga, tidak ada langkah build.
 *
 * Batas dengar dijaga di sini dengan ambang RMS sederhana -- bukan Silero VAD.
 * Aset `public/vad` + `public/ort` (±89 MB) sengaja TIDAK dipakai: bundel vad-web
 * yang vendored adalah UMD, bukan ESM, sehingga `import { MicVAD }` darinya tidak
 * bisa dilakukan tanpa langkah bundling yang sudah dibuang dari proyek ini.
 */

const LAJU_STT = 16000;      // satu-satunya laju yang dimengerti Whisper
const AMBANG_DENGAR = 0.012; // sejalan dengan LANTAI_NOISE di suara.js
const DIAM_SELESAI = 900;    // ms hening setelah bicara -> kalimat dianggap selesai
const DIAM_KOSONG = 6000;    // ms tanpa suara sama sekali -> batalkan
const MAKS_REKAM = 30000;    // ms; server menolak di atas VTUBER_STT_MAKS_DETIK

let ctx = null;
let streamMic = null;
let simpulProses = null;
let bingkai = [];
let merekam = false;
let sudahBicara = false;
let waktuSuaraTerakhir = 0;
let waktuMulai = 0;

// Ditulis saat pasangKontrolMikrofon(): jedaMikrofon() dipanggil dari chat.js tanpa
// tahu elemen apa pun, jadi elemennya disimpan di sini.
let elInput = null;
let fnKirim = (/** @type {string} */ _teks) => {};
let ubahStatus = (/** @type {boolean} */ _aktif, /** @type {string} */ _ket) => {};

/** @returns {boolean} peramban bisa merekam (jalur lokal tidak butuh yang lain) */
export function apakahMicTersedia() {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

/**
 * @param {Float32Array[]} potongan
 * @param {number} laju
 * @param {number} target
 */
function gabungDanResample(potongan, laju, target) {
  let total = 0;
  for (const p of potongan) total += p.length;
  const semua = new Float32Array(total);
  let geser = 0;
  for (const p of potongan) {
    semua.set(p, geser);
    geser += p.length;
  }
  if (laju === target || total === 0) return semua;

  // Interpolasi linear: cukup untuk ucapan, dan tidak butuh pustaka apa pun.
  const panjangBaru = Math.max(1, Math.round((total * target) / laju));
  const hasil = new Float32Array(panjangBaru);
  const langkah = (total - 1) / panjangBaru;
  for (let i = 0; i < panjangBaru; i++) {
    const pos = i * langkah;
    const a = Math.floor(pos);
    const b = Math.min(total - 1, a + 1);
    const pecahan = pos - a;
    hasil[i] = semua[a] * (1 - pecahan) + semua[b] * pecahan;
  }
  return hasil;
}

/** Float32 [-1..1] -> berkas WAV PCM 16-bit mono yang bisa dibaca `wave` di server. */
function keWav(data, laju) {
  const n = data.length;
  const buf = new ArrayBuffer(44 + n * 2);
  const view = new DataView(buf);
  const tulis = (o, teks) => {
    for (let i = 0; i < teks.length; i++) view.setUint8(o + i, teks.charCodeAt(i));
  };
  tulis(0, 'RIFF');
  view.setUint32(4, 36 + n * 2, true);
  tulis(8, 'WAVE');
  tulis(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, laju, true);
  view.setUint32(28, laju * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  tulis(36, 'data');
  view.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) {
    const v = Math.max(-1, Math.min(1, data[i]));
    view.setInt16(44 + i * 2, v < 0 ? v * 0x8000 : v * 0x7fff, true);
  }
  return new Blob([buf], { type: 'audio/wav' });
}

/** Kirim WAV ke server, tunggu teks. Galat dilempar dengan pesan yang bisa dibaca. */
export async function salinAudio(wav) {
  const jawab = await fetch('/api/stt', {
    method: 'POST',
    headers: { 'content-type': 'audio/wav' },
    body: wav,
  });
  if (!jawab.ok) {
    const pesan = await jawab.json().catch(() => ({ error: jawab.statusText }));
    throw new Error(pesan.error || 'STT gagal');
  }
  return (await jawab.json()).teks ?? '';
}

function hentikanRekaman() {
  merekam = false;
  if (simpulProses) {
    try { simpulProses.disconnect(); } catch {}
    simpulProses = null;
  }
  if (streamMic) {
    for (const trek of streamMic.getTracks()) trek.stop();
    streamMic = null;
  }
  if (ctx) {
    try { ctx.close(); } catch {}
    ctx = null;
  }
}

async function kirimHasil() {
  const potongan = bingkai;
  const laju = ctx ? ctx.sampleRate : LAJU_STT;
  bingkai = [];
  hentikanRekaman();
  ubahStatus(false, 'Menyalin suara…');

  const data = gabungDanResample(potongan, laju, LAJU_STT);
  if (data.length < LAJU_STT * 0.3) {
    ubahStatus(false, 'Terlalu pendek — coba lagi');
    setTimeout(() => { elInput.placeholder = 'Katakan sesuatu…'; }, 2500);
    return;
  }
  try {
    const teks = (await salinAudio(keWav(data, LAJU_STT))).trim();
    if (teks) {
      ubahStatus(false);
      elInput.value = '';
      fnKirim(teks);
      return;
    }
    ubahStatus(false, 'Tidak ada yang terdengar');
  } catch (err) {
    ubahStatus(false, `STT: ${err.message}`);
  }
  setTimeout(() => { elInput.placeholder = 'Katakan sesuatu…'; }, 3500);
}

function mulaiMerekam() {
  if (merekam) return;
  bingkai = [];
  sudahBicara = false;

  navigator.mediaDevices
    .getUserMedia({
      audio: {
        // noiseSuppression/autoGainControl sengaja dimatikan: keduanya mengubah
        // audio sebelum kami dengar, dan hasil yang sudah "dipoles" justru lebih
        // buruk di Whisper. echoCancellation tetap on supaya suara Elaina sendiri
        // tidak ikut tertangkap.
        echoCancellation: true,
        noiseSuppression: false,
        autoGainControl: false,
      },
    })
    .then((mic) => {
      streamMic = mic;
      ctx = new AudioContext({ sampleRate: LAJU_STT });
      const sumber = ctx.createMediaStreamSource(mic);
      simpulProses = ctx.createScriptProcessor(4096, 1, 1);

      waktuMulai = Date.now();
      waktuSuaraTerakhir = waktuMulai;
      merekam = true;
      ubahStatus(true);

      simpulProses.onaudioprocess = (event) => {
        if (!merekam) return;
        const masuk = new Float32Array(event.inputBuffer.getChannelData(0));
        bingkai.push(masuk);

        let jumlahKuadrat = 0;
        for (let i = 0; i < masuk.length; i++) jumlahKuadrat += masuk[i] * masuk[i];
        const rms = Math.sqrt(jumlahKuadrat / masuk.length);
        const sekarang = Date.now();

        if (rms > AMBANG_DENGAR) {
          sudahBicara = true;
          waktuSuaraTerakhir = sekarang;
        } else if (sudahBicara && sekarang - waktuSuaraTerakhir > DIAM_SELESAI) {
          kirimHasil();
          return;
        }
        if (!sudahBicara && sekarang - waktuMulai > DIAM_KOSONG) {
          hentikanRekaman();
          ubahStatus(false, 'Tidak ada suara');
          setTimeout(() => { elInput.placeholder = 'Katakan sesuatu…'; }, 2500);
          return;
        }
        if (sekarang - waktuMulai > MAKS_REKAM) kirimHasil();
      };
      sumber.connect(simpulProses);
      // ScriptProcessor hanya dipanggil kalau tersambung ke keluaran; gain 0 membuat
      // mic tidak memantul ke speaker.
      const hening = ctx.createGain();
      hening.gain.value = 0;
      simpulProses.connect(hening);
      hening.connect(ctx.destination);
    })
    .catch((err) => {
      hentikanRekaman();
      const nama = err && err.name ? err.name : 'galat';
      if (nama === 'NotAllowedError' || nama === 'SecurityError') {
        ubahStatus(false);
        alert('Izin mikrofon tidak diberikan. Klik ikon gembok / izin mikrofon pada address bar browser Anda.');
      } else if (nama === 'NotFoundError') {
        ubahStatus(false, 'Tidak ada mikrofon terpasang');
      } else {
        ubahStatus(false, `Mic: ${nama}`);
      }
      setTimeout(() => { elInput.placeholder = 'Katakan sesuatu…'; }, 3500);
    });
}

function berhentiMerekam() {
  if (!merekam) return;
  if (!sudahBicara) {
    hentikanRekaman();
    bingkai = [];
    ubahStatus(false);
    return;
  }
  kirimHasil();
}

function setStatusMic(btnMic, inputEl, aktif, keterangan = '') {
  btnMic.dataset.mendengar = aktif ? 'true' : 'false';
  btnMic.title = aktif ? 'Merekam... klik untuk berhenti & kirim' : 'Bicara lewat mikrofon (id-ID, lokal)';
  btnMic.textContent = aktif ? '🔴' : '🎙️';
  inputEl.placeholder = keterangan || 'Katakan sesuatu…';
}

/**
 * Pasang kontrol tombol mikrofon ke input chat.
 *
 * @param {HTMLButtonElement} btnMic
 * @param {HTMLInputElement} inputEl
 * @param {(teks: string) => void} onKirim
 */
export function pasangKontrolMikrofon(btnMic, inputEl, onKirim) {
  if (!btnMic || !inputEl) return;

  elInput = inputEl;
  fnKirim = onKirim;
  ubahStatus = (aktif, keterangan) => setStatusMic(btnMic, inputEl, aktif, keterangan);

  if (!apakahMicTersedia()) {
    btnMic.title = 'Browser tidak mendukung perekaman audio. Gunakan Chrome / Edge / Firefox terbaru.';
    btnMic.style.opacity = '0.4';
    btnMic.onclick = (e) => {
      e.preventDefault();
      alert('Perekaman suara membutuhkan browser dengan navigator.mediaDevices.getUserMedia.');
    };
    return;
  }

  btnMic.onclick = (e) => {
    e.preventDefault();
    if (merekam) berhentiMerekam();
    else mulaiMerekam();
  };
}

/**
 * Buang rekaman yang sedang berjalan -- dipanggil saat Elaina mulai bicara supaya
 * suaranya sendiri tidak masuk sebagai pertanyaan Master. Sengaja BUANG, bukan
 * kirim: yang tertangkap pada titik itu sudah pasti suara dia sendiri.
 */
export function jedaMikrofon() {
  if (!merekam) return;
  bingkai = [];
  hentikanRekaman();
  ubahStatus(false);
}

export function lanjutMikrofon() {
  /* tidak ada yang ditahan permanen; tombolnya manual */
}
