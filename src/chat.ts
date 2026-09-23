import { EKSPRESI_DASAR, TAG_KE_EKSPRESI, kupasTag } from './ekspresi';
import { bicarakan, hentikan } from './suara';
import { jedaMikrofon, lanjutMikrofon, nyalakanMikrofon, salinAudio } from './mikrofon';

type Pesan = { role: 'user' | 'assistant'; content: string };

const KUNCI_RIWAYAT = 'vtuber.riwayat';

function muat(): Pesan[] {
  try {
    const raw = localStorage.getItem(KUNCI_RIWAYAT);
    const data = raw ? JSON.parse(raw) : [];
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function simpan(riwayat: Pesan[]) {
  localStorage.setItem(KUNCI_RIWAYAT, JSON.stringify(riwayat.slice(-40)));
}

function gelembung(role: Pesan['role'], teks: string) {
  const el = document.createElement('div');
  el.className = `pesan ${role}`;
  el.textContent = teks;
  document.getElementById('log')!.appendChild(el);
  el.scrollIntoView({ block: 'end' });
  return el;
}

export function pasangChat(picuEkspresi: (ekspresi: string) => void) {
  const riwayat = muat();
  const form = document.getElementById('form') as HTMLFormElement;
  const isi = document.getElementById('isi') as HTMLInputElement;
  const health = document.getElementById('health') as HTMLElement;
  const micStatus = document.getElementById('mikrofon') as HTMLElement;
  const micBtn = document.getElementById('mic') as HTMLButtonElement;
  let sibuk = false;
  let micHidup = false;

  fetch('/api/health')
    .then((r) => r.json())
    .then((h) => {
      health.textContent = h.key ? `sisi server siap — ${h.model}` : 'API key belum diisi';
    })
    .catch(() => {
      health.textContent = 'sisi server tidak jalan (npm run server)';
    });

  riwayat.forEach((p) => gelembung(p.role, p.content));

  async function kirim(teks: string) {
    if (sibuk) {
      micStatus.textContent = 'lagi sibuk, tunggu sebentar';
      return;
    }

    sibuk = true;
    hentikan();
    gelembung('user', teks);
    riwayat.push({ role: 'user', content: teks });

    const target = gelembung('assistant', '');
    let adaTag = false;
    const kupas = kupasTag((tag) => {
      const nama = TAG_KE_EKSPRESI[tag];
      if (nama) {
        picuEkspresi(nama);
        adaTag = true;
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
      for (;;) {
        const { done, value } = await pembaca.read();
        if (done) break;
        jawaban += kupas.tulis(dekode.decode(value, { stream: true }));
        target.textContent = jawaban;
      }
      jawaban += kupas.tutup();
      // Tag yang dibuang meninggalkan spasi liar di awal dan di antara kalimat.
      jawaban = jawaban.replace(/[ \t]{2,}/g, ' ').trim();
      target.textContent = jawaban;

      riwayat.push({ role: 'assistant', content: jawaban });
      simpan(riwayat);
      if (!adaTag) picuEkspresi(EKSPRESI_DASAR);
      void ucapkan(jawaban);
    } catch (err) {
      target.textContent = `gagal kirim: ${err instanceof Error ? err.message : String(err)}`;
      target.classList.add('gagal');
      riwayat.pop();
    } finally {
      sibuk = false;
      isi.focus();
    }
  }

  async function ucapkan(teks: string) {
    const el = document.getElementById('suara');
    if (!el) return;
    // Setengah dupleks: mikrofon ditahan supaya dia tidak menyalin suaranya sendiri.
    jedaMikrofon();
    el.textContent = 'menyusun suara…';
    try {
      await bicarakan(teks);
      el.textContent = 'diam';
    } catch (err) {
      el.textContent = `gagal: ${err instanceof Error ? err.message : String(err)}`;
    } finally {
      if (micHidup) lanjutMikrofon();
    }
  }

  micBtn.onclick = async () => {
    if (micHidup) return;
    micBtn.disabled = true;
    micStatus.textContent = 'menyalakan…';
    try {
      await nyalakanMikrofon(
        async (wav) => {
          if (sibuk) return;
          micStatus.textContent = 'menyalin…';
          try {
            const teks = await salinAudio(wav);
            if (!teks) {
              micStatus.textContent = 'tidak terdengar';
              return;
            }
            micStatus.textContent = `kamu: ${teks}`;
            await kirim(teks);
          } catch (err) {
            micStatus.textContent = `STT gagal: ${err instanceof Error ? err.message : String(err)}`;
          }
        },
        (s) => {
          micStatus.textContent = s;
        },
      );
      micHidup = true;
      micStatus.textContent = 'aktif, bicara saja';
    } catch (err) {
      micStatus.textContent = `mikrofon ditolak: ${err instanceof Error ? err.message : String(err)}`;
    } finally {
      micBtn.disabled = false;
    }
  };

  form.onsubmit = (e) => {
    e.preventDefault();
    const teks = isi.value.trim();
    if (!teks) return;
    isi.value = '';
    void kirim(teks);
  };
}
