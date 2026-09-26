/**
 * Jalur mikrofon (Speech-to-Text).
 *
 * Menggunakan Web Speech API (SpeechRecognition / webkitSpeechRecognition)
 * bawaan browser Chromium (Chrome, Edge, Brave, dll.) untuk deteksi suara bahasa Indonesia (id-ID)
 * secara real-time tanpa latensi dan tanpa beban CPU.
 */

// Deteksi konstruktor pengenal suara peramban
function dapatkanSpeechRecognition() {
  if (typeof window === 'undefined') return null;
  const w = /** @type {any} */ (window);
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

let recognizer = null;
let sedangMendengar = false;
let jedaSementara = false;
let kirimOtomatisTimer = null;

export function apakahMicTersedia() {
  return dapatkanSpeechRecognition() !== null;
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

  const SpeechClass = dapatkanSpeechRecognition();
  if (!SpeechClass) {
    btnMic.title = 'Browser tidak mendukung SpeechRecognition. Gunakan Google Chrome / Microsoft Edge.';
    btnMic.style.opacity = '0.4';
    btnMic.onclick = (e) => {
      e.preventDefault();
      alert('Fitur suara membutuhkan browser berbasis Chromium (Google Chrome, Microsoft Edge, Brave, Opera).');
    };
    return;
  }

  function setStatusMic(aktif, keterangan = '') {
    sedangMendengar = aktif;
    btnMic.dataset.mendengar = aktif ? 'true' : 'false';
    btnMic.title = aktif ? 'Mendengarkan... klik untuk berhenti' : 'Bicara lewat mikrofon (id-ID)';
    btnMic.textContent = aktif ? '🔴' : '🎙️';
    if (keterangan) {
      inputEl.placeholder = keterangan;
    } else {
      inputEl.placeholder = 'Katakan sesuatu…';
    }
  }

  function mulaiMendengar() {
    if (recognizer) {
      try { recognizer.abort(); } catch {}
    }
    if (kirimOtomatisTimer) {
      clearTimeout(kirimOtomatisTimer);
      kirimOtomatisTimer = null;
    }

    try {
      recognizer = new SpeechClass();
      recognizer.lang = 'id-ID'; // Bahasa Indonesia
      recognizer.continuous = false; // satu giliran bicara
      recognizer.interimResults = true;
      recognizer.maxAlternatives = 1;

      let kalimatTerakhir = '';

      recognizer.onstart = () => {
        setStatusMic(true, 'Mendengarkan suara Anda (id-ID)…');
      };

      recognizer.onresult = (event) => {
        let teksFinal = '';
        let teksSementara = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const res = event.results[i];
          if (res.isFinal) {
            teksFinal += res[0].transcript;
          } else {
            teksSementara += res[0].transcript;
          }
        }

        const teksLengkap = (teksFinal || teksSementara).trim();
        if (teksLengkap) {
          kalimatTerakhir = teksLengkap;
          inputEl.value = teksLengkap;
        }

        // Jika kalimat sudah final, jadwalkan kirim otomatis dengan jeda singkat
        if (teksFinal.trim()) {
          kalimatTerakhir = teksFinal.trim();
          if (kirimOtomatisTimer) clearTimeout(kirimOtomatisTimer);
          kirimOtomatisTimer = setTimeout(() => {
            const pesan = kalimatTerakhir.trim();
            if (pesan) {
              setStatusMic(false);
              inputEl.value = '';
              kalimatTerakhir = '';
              onKirim(pesan);
            }
          }, 600);
        }
      };

      recognizer.onerror = (event) => {
        const galat = event.error || '';
        console.warn('Mikrofon event error:', galat);

        if (galat === 'not-allowed' || galat === 'service-not-allowed') {
          setStatusMic(false);
          alert('Izin mikrofon tidak diberikan. Silakan klik ikon gembok / izin mikrofon pada address bar browser Anda.');
        } else if (galat === 'no-speech') {
          // Hanya diam tidak ada suara, reset ke keadaan normal
          setStatusMic(false);
        } else if (galat !== 'aborted') {
          setStatusMic(false, `Mic error: ${galat}`);
          setTimeout(() => { inputEl.placeholder = 'Katakan sesuatu…'; }, 3000);
        } else {
          setStatusMic(false);
        }
      };

      recognizer.onend = () => {
        if (!jedaSementara) {
          setStatusMic(false);
        }
        // Jika ada kalimat yang tertampung tapi belum terkirim
        if (kalimatTerakhir.trim() && !kirimOtomatisTimer) {
          const pesan = kalimatTerakhir.trim();
          inputEl.value = '';
          kalimatTerakhir = '';
          onKirim(pesan);
        }
      };

      recognizer.start();
    } catch (err) {
      console.error('Gagal menginisialisasi mikrofon:', err);
      setStatusMic(false);
    }
  }

  function berhentiMendengar() {
    if (kirimOtomatisTimer) {
      clearTimeout(kirimOtomatisTimer);
      kirimOtomatisTimer = null;
    }
    if (recognizer) {
      try { recognizer.stop(); } catch {}
    }
    setStatusMic(false);
  }

  btnMic.onclick = (e) => {
    e.preventDefault();
    if (sedangMendengar) {
      berhentiMendengar();
    } else {
      mulaiMendengar();
    }
  };
}

/** Tahan mikrofon saat avatar berbicara agar suaranya sendiri tidak tertranskrip */
export function jedaMikrofon() {
  if (sedangMendengar && recognizer) {
    jedaSementara = true;
    try { recognizer.abort(); } catch {}
  }
}

export function lanjutMikrofon() {
  jedaSementara = false;
}

/** Fallback kirim audio WAV ke /api/stt jika diperlukan */
export async function salinAudio(wav) {
  const res = await fetch('/api/stt', {
    method: 'POST',
    headers: { 'content-type': 'audio/wav' },
    body: wav,
  });

  if (!res.ok) {
    const pesan = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(pesan.error ?? 'STT gagal');
  }

  return (await res.json()).teks ?? '';
}
