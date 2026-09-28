import { EKSPRESI_DASAR, NAMA_GERAK, NAMA_POSE, NAMA_WAJAH, kupasTag } from './ekspresi.js';
import { kalimatSiap } from './kalimat.js';
import { jedaMikrofon, lanjutMikrofon, pasangKontrolMikrofon } from './mikrofon.js';
import { antre, bicarakan, hentikan, pasangStatusSuara, selesai } from './suara.js';

const KUNCI_RIWAYAT = 'vtuber.riwayat';

function muat() {
  try {
    const raw = localStorage.getItem(KUNCI_RIWAYAT);
    const data = raw ? JSON.parse(raw) : [];
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function simpan(riwayat) {
  localStorage.setItem(KUNCI_RIWAYAT, JSON.stringify(riwayat.slice(-40)));
}

function gelembung(role, teks) {
  const el = document.createElement('div');
  el.className = `pesan ${role}`;
  el.textContent = teks;
  document.getElementById('log').appendChild(el);
  el.scrollIntoView({ block: 'end' });
  return el;
}

const API_BASE = typeof window !== 'undefined' && window.location?.protocol === 'file:'
  ? 'http://127.0.0.1:8787'
  : '';

/**
 * @param {(nama: string) => void} picuEkspresi
 * @param {(nama: string, hidup: boolean) => void} picuPose
 * @param {(nama: string, prioritas: number) => boolean} picuGerak false = tidak jadi jalan
 * @param {(apa: 'kirim' | 'gerak') => void} catat untuk mesin keadaan, lihat web/keadaan.js
 */
export function pasangChat(picuEkspresi, picuPose = () => {}, picuGerak = () => false, catat = () => {}) {
  const riwayat = muat();
  const form = document.getElementById('form');
  const isi = document.getElementById('isi');
  const health = document.getElementById('health');
  let sibuk = false;
  // Bicara per kalimat menyambung satu panggilan TTS lagi, jadi batas permintaan
  // per menit bisa jadi alasan untuk mematikannya: VTUBER_TTS_PER_KALIMAT=false.
  let perKalimat = true;
  const suaraEl = document.getElementById('suara');
  /**
   * Satu-satunya tempat keadaan suara ditulis. Teksnya ditampilkan di UI dan
   * atribut data-keadaan dibaca lampu indikator di index.html. Lewat satu
   * fungsi begini keduanya tidak bisa saling meninggalkan.
   */
  const setSuara = (teks) => {
    if (!suaraEl) return;
    suaraEl.textContent = teks;
    suaraEl.dataset.keadaan = teks.startsWith('gagal')
      ? 'gagal'
      : teks === 'diam'
        ? 'diam'
        : 'berbicara';
  };

  pasangStatusSuara((keadaan) => {
    if (keadaan === 'berbicara') setSuara('berbicara');
  });

  fetch(`${API_BASE}/api/health`)
    .then((r) => r.json())
    .then((h) => {
      perKalimat = h?.tts?.perKalimat ?? true;
      const suara = h?.tts?.model ? ` · suara ${h.tts.model}` : '';
      const sisi = h?.sisi ? ` · sisi ${h.sisi}` : '';
      health.textContent = h.key ? `sisi server siap — ${h.model}${suara}${sisi}` : 'API key belum diisi';
    })
    .catch(() => {
      health.textContent = 'sisi server tidak jalan (python main.py)';
    });

  riwayat.forEach((p) => gelembung(p.role, p.content));

  const btnChatBaru = document.getElementById('chat-baru');
  if (btnChatBaru) {
    btnChatBaru.onclick = () => {
      if (sibuk) return;
      hentikan();
      riwayat.length = 0;
      localStorage.removeItem(KUNCI_RIWAYAT);
      const log = document.getElementById('log');
      if (log) log.innerHTML = '';
      setSuara('diam');
      picuEkspresi(EKSPRESI_DASAR);
      isi.focus();
    };
  }

  async function kirim(teks) {
    if (sibuk) return;

    sibuk = true;
    // Awal balasan: mesin keadaan butuh tahu bahwa ini bukan sisa waktu idle,
    // dan bahwa gerakan balasan belum tentu membawa tag [gerak:] sendiri.
    catat('kirim');
    jedaMikrofon();
    hentikan();
    gelembung('user', teks);
    riwayat.push({ role: 'user', content: teks });

    const target = gelembung('assistant', '');
    // Tag wajah mengganti raut; [prop:nama] menyalakan pose DI ATAS raut itu.
    let adaWajah = false;
    const kupas = kupasTag((tag) => {
      const prop = /^prop[:=](.+)$/.exec(tag);
      if (prop) {
        const [nama, mode] = prop[1].split(/[=:]/);
        // [prop:kosong] adalah janji persona.md:96: lepas SEMUA aksesoris, bukan
        // satu pose bernama "kosong".
        if (nama === 'kosong') {
          for (const n of NAMA_POSE) picuPose(n, false);
          return;
        }
        if (!NAMA_POSE.has(nama)) console.warn('tag pose tidak dikenal:', tag);
        else picuPose(nama, !/^(mati|off|false|0)$/.test(mode ?? ''));
        return;
      }
      const gerak = /^gerak[:=](.+)$/.exec(tag);
      if (gerak) {
        const nama = gerak[1].split(/[=:]/)[0].trim();
        if (nama !== 'kosong' && !NAMA_GERAK.has(nama)) console.warn('tag gerakan tidak dikenal:', tag);
        else {
          // Ditandai lebih dulu, tanpa menunggu motionnya jadi: yang perlu
          // diketahui mesin keadaan hanyalah "balasan ini sudah punya gerakan
          // sendiri", bukan apakah pustaka memberinya giliran.
          picuGerak(nama, 3);
          catat('gerak');
        }
        return;
      }
      if (NAMA_WAJAH.has(tag)) {
        picuEkspresi(tag);
        adaWajah = true;
      } else {
        console.warn('tag ekspresi tidak dikenal:', tag);
      }
    });

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ messages: riwayat }),
      });

      if (!res.ok || !res.body) {
        const pesan = await res.json().catch(() => ({ error: res.statusText }));
        target.textContent = `error: ${pesan.error ?? 'tidak diketahui'}`;
        target.classList.add('gagal');
        riwayat.pop();
        return;
      }

      const pembaca = res.body.getReader();
      const dekode = new TextDecoder();
      let jawaban = '';
      // Suara jalan berbarengan dengan teks: begitu satu kalimat selesai,
      // suaranya langsung diantre -- tidak menunggu jawaban lengkap (yang dulu
      // berarti menunggu 5-25 dtk teks PLUS 50-77 dtk sintesis).
      let terucap = 0;
      let antrean = 0;
      let potonganGagal = 0;
      let pesanGagal = '';
      const catat = (err) => {
        potonganGagal += 1;
        pesanGagal = err instanceof Error ? err.message : String(err);
      };
      const siarkan = () => {
        if (!perKalimat) return;
        const sisaDari = jawaban.slice(terucap);
        // Selalu potong per kalimat utuh (tanpa potong koma), agar RVC
        // menyelaraskan kalimat utuh dan pitch vokal Silver Wolf tidak terpotong.
        const { siap, sisa } = kalimatSiap(sisaDari, false);
        if (!siap.length) return;
        terucap += sisaDari.length - sisa.length;
        setSuara('menyelaraskan suara Silver Wolf (RVC)…');
        for (const potongan of siap) {
          antrean += 1;
          antre(potongan).catch(catat);
        }
      };
      for (;;) {
        const { done, value } = await pembaca.read();
        if (done) break;
        jawaban += kupas.tulis(dekode.decode(value, { stream: true }));
        target.textContent = jawaban;
        siarkan();
      }
      jawaban += kupas.tutup();
      // Tag yang dibuang meninggalkan spasi liar di awal dan di antara kalimat.
      jawaban = jawaban.replace(/[ \t]{2,}/g, ' ').trim();
      target.textContent = jawaban;

      riwayat.push({ role: 'assistant', content: jawaban });
      simpan(riwayat);
      if (!adaWajah) picuEkspresi(EKSPRESI_DASAR);
      // Potongan penutup, lalu tunggu antrean habis terputar. Semua potongan
      // gugur = suara mati total dan itu harus kelihatan di layar; satu-dua yang
      // gugur cukup masuk log.
      if (perKalimat) {
        const sisa = jawaban.slice(terucap);
        if (sisa.trim()) {
          antrean += 1;
          setSuara('menyelaraskan suara Silver Wolf (RVC)…');
          antre(sisa).catch(catat);
        }
        await selesai();
        const matiTotal = antrean > 0 && potonganGagal === antrean;
        setSuara(matiTotal ? `gagal: ${pesanGagal}` : 'diam');
        if (potonganGagal && !matiTotal) console.warn(`${potonganGagal} dari ${antrean} potongan suara gugur`);
      } else {
        try {
          await bicarakan(jawaban);
          setSuara('diam');
        } catch (err) {
          setSuara(`gagal: ${err instanceof Error ? err.message : String(err)}`);
        }
      }
    } catch (err) {
      target.textContent = `gagal kirim: ${err instanceof Error ? err.message : String(err)}`;
      target.classList.add('gagal');
      riwayat.pop();
    } finally {
      sibuk = false;
      lanjutMikrofon();
      isi.focus();
    }
  }

  const btnMic = document.getElementById('btn-mic');
  if (btnMic) {
    pasangKontrolMikrofon(btnMic, isi, (teksSuara) => {
      void kirim(teksSuara);
    });
  }

  form.onsubmit = (e) => {
    e.preventDefault();
    const teks = isi.value.trim();
    if (!teks) return;
    isi.value = '';
    void kirim(teks);
  };
}
