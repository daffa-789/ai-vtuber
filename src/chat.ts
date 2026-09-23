import { EKSPRESI_DASAR, TAG_KE_EKSPRESI, kupasTag } from './ekspresi';
import { bicarakan } from './suara';

type Pesan = { role: 'user' | 'assistant'; content: string };

const KUNCI_RIWAYAT = 'vtuber.riwayat';

async function ucapkan(teks: string) {
  const el = document.getElementById('suara');
  if (!el) return;
  el.textContent = 'menyusun suara…';
  try {
    await bicarakan(teks);
    el.textContent = 'diam';
  } catch (err) {
    el.textContent = `gagal: ${err instanceof Error ? err.message : String(err)}`;
  }
}

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
  let sibuk = false;

  fetch('/api/health')
    .then((r) => r.json())
    .then((h) => {
      health.textContent = h.key ? `sisi server siap — ${h.model}` : 'API key belum diisi';
    })
    .catch(() => {
      health.textContent = 'sisi server tidak jalan (npm run server)';
    });

  riwayat.forEach((p) => gelembung(p.role, p.content));

  form.onsubmit = async (e) => {
    e.preventDefault();
    const teks = isi.value.trim();
    if (!teks || sibuk) return;

    sibuk = true;
    isi.value = '';
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
  };
}
