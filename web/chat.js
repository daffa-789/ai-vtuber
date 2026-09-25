import { EKSPRESI_DASAR, NAMA_POSE, NAMA_WAJAH, kupasTag } from './ekspresi.js';
import { kalimatSiap } from './kalimat.mjs';
import { antre, bicarakan, hentikan, selesai } from './suara.js';

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

export function pasangChat(picuEkspresi, picuPose = () => {}) {
  const riwayat = muat();
  const form = document.getElementById('form');
  const isi = document.getElementById('isi');
  const health = document.getElementById('health');
  let sibuk = false;
  // Bicara per kalimat menyambung satu panggilan TTS lagi, jadi batas permintaan
  // per menit bisa jadi alasan untuk mematikannya: VTUBER_TTS_PER_KALIMAT=false.
  let perKalimat = true;
  const suaraEl = document.getElementById('suara');

  fetch('/api/health')
    .then((r) => r.json())
    .then((h) => {
      perKalimat = h?.tts?.perKalimat ?? true;
      const suara = h?.tts?.model ? ` · suara ${h.tts.model}` : '';
      const sisi = h?.sisi ? ` · sisi ${h.sisi}` : '';
      health.textContent = h.key ? `sisi server siap — ${h.model}${suara}${sisi}` : 'API key belum diisi';
    })
    .catch(() => {
      health.textContent = 'sisi server tidak jalan (python server_py/app.py)';
    });

  riwayat.forEach((p) => gelembung(p.role, p.content));

  async function kirim(teks) {
    if (sibuk) return;

    sibuk = true;
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
        if (!NAMA_POSE.has(nama)) console.warn('tag pose tidak dikenal:', tag);
        else picuPose(nama, !/^(mati|off|false|0)$/.test(mode ?? ''));
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
      const res = await fetch('/api/chat', {
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
      // Potongan di koma cuma boleh terjadi sekali, itu untuk kalimat pertama.
      let bolehPotongAwal = true;
      const catat = (err) => {
        potonganGagal += 1;
        pesanGagal = err instanceof Error ? err.message : String(err);
      };
      const siarkan = () => {
        if (!perKalimat) return;
        const sisaDari = jawaban.slice(terucap);
        const { siap, sisa } = kalimatSiap(sisaDari, bolehPotongAwal);
        if (!siap.length) return;
        bolehPotongAwal = false;
        terucap += sisaDari.length - sisa.length;
        if (suaraEl) suaraEl.textContent = 'menyusun suara…';
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
      if (suaraEl) suaraEl.textContent = 'menyusun suara…';
      if (perKalimat) {
        const sisa = jawaban.slice(terucap);
        if (sisa.trim()) {
          antrean += 1;
          antre(sisa).catch(catat);
        }
        await selesai();
        const matiTotal = antrean > 0 && potonganGagal === antrean;
        if (suaraEl) suaraEl.textContent = matiTotal ? `gagal: ${pesanGagal}` : 'diam';
        if (potonganGagal && !matiTotal) console.warn(`${potonganGagal} dari ${antrean} potongan suara gugur`);
      } else {
        try {
          await bicarakan(jawaban);
          if (suaraEl) suaraEl.textContent = 'diam';
        } catch (err) {
          if (suaraEl) suaraEl.textContent = `gagal: ${err instanceof Error ? err.message : String(err)}`;
        }
      }
    } catch (err) {
      target.textContent = `gagal kirim: ${err instanceof Error ? err.message : String(err)}`;
      target.classList.add('gagal');
      riwayat.pop();
    } finally {
      sibuk = false;
      isi.focus();
    }
  }

  form.onsubmit = (e) => {
    e.preventDefault();
    const teks = isi.value.trim();
    if (!teks) return;
    isi.value = '';
    void kirim(teks);
  };
}
