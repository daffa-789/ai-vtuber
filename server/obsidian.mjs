// Transport catatan karakter ke vault Obsidian. Token dibaca dari
// ~/.qoder/settings.json (mcpServers.obsidian) -- sama seperti yang dipakai
// scripts/sync-memory-to-obsidian.mjs, jadi tidak ada rahasia baru di proyek ini.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';

function bacaKonfig() {
  try {
    const s = JSON.parse(readFileSync(join(homedir(), '.qoder', 'settings.json'), 'utf8'));
    const o = s.mcpServers?.obsidian;
    const auth = o?.headers?.Authorization;
    if (!o?.url || !auth) return null;
    return { base: new URL(o.url).origin, auth };
  } catch {
    return null;
  }
}

const KONF = bacaKonfig();
const PANGKAL = 'Waifu Memory/AI VTUBER';

export const tersedia = () => Boolean(KONF);
export const alasanTidakTersedia = () =>
  KONF ? null : 'mcpServers.obsidian tidak ditemukan di ~/.qoder/settings.json';

const alamat = (p) => `${KONF.base}/vault/${encodeURIComponent(p).replace(/%2F/g, '/')}`;

async function unduh(p, method, body) {
  const r = await fetch(alamat(p), {
    method,
    headers: { Authorization: KONF.auth, ...(body ? { 'Content-Type': 'text/markdown' } : {}) },
    body,
  });
  if (!r.ok && r.status !== 404) throw new Error(`Obsidian ${r.status} untuk ${p}`);
  return r;
}

const tanggal = () => new Date().toISOString().slice(0, 10);

// Links wajib ditulis di sini: tanpa field `links`, file hasil auto-save jadi
// node yatim di graph view Obsidian (penyebab "Mood"/"Fakta" tidak tersambung).
const TAUTAN_DASAR = ['haru-persona', '_Index'];

function kerangka(nama, judul, isi, tautan = []) {
  const links = [...new Set([...TAUTAN_DASAR, ...tautan])];
  return [
    '---',
    'type: memory',
    'kind: karakter',
    `name: "${nama}"`,
    `description: "${judul}"`,
    'project: "Desktop AI VTUBER"',
    `updated: "${tanggal()}"`,
    'tags:',
    '  - "memory/karakter"',
    '  - "project/Desktop AI VTUBER"',
    'links:',
    ...links.map((l) => `  - "[[${l}]]"`),
    '---',
    '',
    `# ${judul}`,
    '',
    isi.trim(),
    '',
  ].join('\n');
}

// ── Fakta: daftar yang dia ingat tentang user.
export async function simpanFakta(fakta) {
  const isi = fakta.length ? fakta.map((f) => `- ${f}`).join('\n') : '_Belum ada fakta tersimpan._';
  await unduh(
    `${PANGKAL}/Fakta.md`,
    'PUT',
    kerangka('fakta-haru', 'Fakta yang Haru ingat tentang Master', isi, ['Mood', 'Quotes', 'Riwayat']),
  );
}

export async function bacaFakta() {
  const r = await unduh(`${PANGKAL}/Fakta.md`, 'GET');
  if (!r.ok) return [];
  return (await r.text())
    .split('\n')
    .filter((l) => l.startsWith('- '))
    .map((l) => l.slice(2).trim())
    .filter((l) => l && !l.startsWith('_'));
}

// ── Mood: state emosional, dibaca ulang tiap percakapan.
export async function simpanMood(mood) {
  const isi = [
    `Valensi: ${mood.valensi.toFixed(2)} (-1 berat .. +1 senang)`,
    `Energi: ${mood.energi.toFixed(2)}`,
    `Afinitas: ${mood.afinitas.toFixed(2)} (0 jauh .. 1 dekat)`,
    `Pertukaran tercatat: ${mood.pertukaran}`,
    `Terakhir diperbarui: ${new Date().toISOString()}`,
    mood.alasan ? `Alasan: ${mood.alasan}` : '',
  ]
    .filter(Boolean)
    .join('\n');
  await unduh(
    `${PANGKAL}/Mood.md`,
    'PUT',
    kerangka('mood-haru', 'Suasana hati Haru saat ini', isi, ['Fakta', 'Quotes', 'Riwayat']),
  );
}

export async function bacaMood() {
  const r = await unduh(`${PANGKAL}/Mood.md`, 'GET');
  if (!r.ok) return null;
  const teks = await r.text();
  const ambil = (k) => Number(teks.match(new RegExp(`${k}: (-?[\\d.]+)`))?.[1]);
  const valensi = ambil('Valensi');
  const energi = ambil('Energi');
  const afinitas = ambil('Afinitas');
  if ([valensi, energi, afinitas].some(Number.isNaN)) return null;
  return {
    valensi,
    energi,
    afinitas,
    pertukaran: Number(teks.match(/Pertukaran tercatat: (\d+)/)?.[1] ?? 0),
  };
}

// ── Riwayat harian: satu catatan per tanggal, ditambah bukan ditimpa.
export async function catatHari(baris) {
  const p = `${PANGKAL}/Riwayat/${tanggal()}.md`;
  const r = await unduh(p, 'GET');
  const lama = r.ok ? await r.text() : '';
  const badan = lama.split('\n').filter((l) => l.startsWith('- '));
  badan.push(`- ${baris}`);
  await unduh(
    p,
    'PUT',
    kerangka(`riwayat-${tanggal()}`, `Riwayat percakapan ${tanggal()}`, badan.join('\n'), [
      'Fakta',
      'Mood',
      'Quotes',
    ]),
  );
}
