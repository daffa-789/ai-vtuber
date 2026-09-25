// Pasang model karakter dari folder sumber (default: New Model/penyihir) ke
// public/models/penyihir dengan nama berkas Indonesia.
//
// Resep wajah, pose, dan gerakan TIDAK lagi ditulis di sini: semuanya dibaca
// dari .env lewat web/konfigurasi.mjs -- modul yang sama dipakai browser.
// Berkas .exp3.json hasil skrip ini cuma salinan supaya alat luar (VTube Studio,
// Cubism Editor) menampilkan wajah yang sama dengan aplikasi.
//
//   node scripts/pasang-model.mjs [folder-sumber]
//
// Folder hasilnya tidak ikut ke git (aset Live2D berlisensi, lihat .gitignore),
// jadi skrip inilah yang merekam pemasangannya: berkas mana yang disalin dan
// bagaimana label Mandarin diterjemahkan.
import { copyFile, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { envDariDisk } from './env.mjs';
import { bacaKonfigurasi, ekspresiKeJson } from '../web/konfigurasi.mjs';

const SUMBER = resolve(process.argv[2] ?? 'New Model/penyihir');
const TUJUAN = resolve('public/models/penyihir');
const NAMA = 'penyihir';

const konfig = bacaKonfigurasi(envDariDisk());
const semuaEkspresi = [...konfig.wajah, ...konfig.pose];

// Berkas sumber yang memang tidak dibutuhkan browser.
const DIABAIKAN = ['Thumbs.db', 'items_pinned_to_model.json'];

// Label parameter Mandarin -> Indonesia, hanya untuk pembaca di editor/Cubism.
// Id tidak pernah disentuh: physics3.json, moc3, dan ekspresi menunjuk ke Id.
const LABEL = {
  Param59: 'mata bintang',
  Param60: 'mata hati',
  Param61: 'memamerkan barang 1',
  Param62: 'memamerkan barang 2',
  Param64: 'hantu kecil peliharaan',
  Param65: 'tangan memeluk',
  Param66: 'kacamata',
  Param67: 'cemberut',
  Param68: 'mata berair',
  Param69: 'keringat muram',
  Param71: 'topi (30 = topi hilang)',
  Param72: 'tongkat sihir',
};

const KAMUS = [
  ['(头发Z)', '(rambut Z)'],
  ['张开和闭合', 'buka-tutup'],
  ['用力挤嘴', 'bibir ditekan'],
  ['身体旋转', 'rotasi tubuh'],
  ['嘴巴宽', 'mulut melebar'],
  ['挤眼睛', 'mata menyipit'],
  ['歪嘴物理', 'fisika mulut miring'],
  ['眼珠物理', 'fisika bola mata'],
  ['眼框物理', 'fisika kelopak'],
  ['小幽灵', 'hantu kecil'],
  ['辫子阴影', 'bayangan kepang'],
  ['耳朵', 'telinga'],
  ['左耳', 'telinga kiri'],
  ['右耳', 'telinga kanan'],
  ['羽毛', 'bulu'],
  ['坠饰', 'gantungan'],
  ['阴影', 'bayangan'],
  ['辫子', 'kepang'],
  ['幽灵', 'hantu'],
  ['左眼', 'mata kiri'],
  ['右眼', 'mata kanan'],
  ['开闭', 'buka-tutup'],
  ['微笑', 'senyum'],
  ['眼球', 'bola mata'],
  ['上下', 'naik-turun'],
  ['変形', 'bentuk'],
  ['变形', 'bentuk'],
  ['嘴部', 'mulut'],
  ['嘴巴', 'mulut'],
  ['舌头', 'lidah'],
  ['歪嘴', 'mulut miring'],
  ['生气', 'marah'],
  ['鼓脸', 'pipi gembung'],
  ['撅嘴', 'bibir monyong'],
  ['嘟嘴', 'bibir membulat'],
  ['下巴', 'rahang'],
  ['星星', 'bintang'],
  ['哭哭', 'menangis'],
  ['招手', 'melambai'],
  ['衣服', 'baju'],
  ['耳坠', 'anting'],
  ['耳环', 'anting'],
  ['挂坠', 'liontin'],
  ['帽子', 'topi'],
  ['头发', 'rambut'],
  ['参数', 'parameter'],
  ['角度', 'sudut'],
  ['呼吸', 'napas'],
  ['惯性', 'lembam'],
  ['身子', 'badan'],
  ['头', 'kepala'],
  ['身', 'badan'],
  ['胸', 'dada'],
  ['耳', 'telinga'],
  ['眉', 'alis'],
  ['眼', 'mata'],
  ['嘴', 'mulut'],
  ['脸', 'wajah'],
  ['心', 'hati'],
  ['飘', 'melayang'],
  [' physics]', ' [fisika]'],
  ['physics]', 'fisika]'],
];

const cari = async (pola) => {
  const ketemu = (await readdir(SUMBER)).find((f) => pola.test(f));
  if (!ketemu) throw new Error(`tidak menemukan berkas ${pola} di ${SUMBER}`);
  return ketemu;
};

const salin = async (dari, ke) => {
  await mkdir(dirname(resolve(TUJUAN, ke)), { recursive: true });
  await copyFile(join(SUMBER, dari), resolve(TUJUAN, ke));
  console.log(`  salin  ${dari} -> ${ke}`);
};

const tulis = async (ke, isi) => {
  await mkdir(dirname(resolve(TUJUAN, ke)), { recursive: true });
  await writeFile(resolve(TUJUAN, ke), isi);
  console.log(`  tulis  ${ke}`);
};

if (!existsSync(SUMBER)) throw new Error(`folder sumber tidak ada: ${SUMBER}`);
// Skrip ini menghapus TUJUAN lebih dulu, jadi pastikan dia benar-benar menunjuk
// ke dalam proyek dan bukan ke hasil cwd yang keliru.
if (!TUJUAN.endsWith(join('public', 'models', NAMA)) || !TUJUAN.includes(resolve('.'))) {
  throw new Error(`jalur tujuan tidak masuk akal: ${TUJUAN}`);
}
await rm(TUJUAN, { recursive: true, force: true });

const moc = await cari(/\.moc3$/);
const physics = await cari(/\.physics3\.json$/);
const cdi = await cari(/\.cdi3\.json$/);
const akar = moc.replace(/\.moc3$/, '');

// Tekstur: model ini datang dengan atlas 8192. Kalau nanti ada atlas ukuran
// lain di folder sumber, pilih lewat VITE_TEKSTUR di .env -- tidak usah edit kode.
const kandidat = [`${akar}.${konfig.tekstur}`, konfig.tekstur].filter((f) => existsSync(join(SUMBER, f)));
if (!kandidat.length) {
  const ada = (await readdir(SUMBER)).filter((f) => /\.\d{3,5}$/.test(f));
  throw new Error(
    `VITE_TEKSTUR="${konfig.tekstur}" tidak ada di ${SUMBER}; yang tersedia: ${ada.join(', ') || '(tidak ada folder tekstur)'}`,
  );
}
const folderTekstur = kandidat[0];

await salin(moc, `${NAMA}.moc3`);
await salin(physics, `${NAMA}.physics3.json`);

const tekstur = (await readdir(join(SUMBER, folderTekstur))).filter(
  (f) => f.endsWith('.png') && !DIABAIKAN.includes(f),
);
for (const t of tekstur) await salin(`${folderTekstur}/${t}`, `tekstur/${t}`);

// Gerakan. Motion aslinya Loop:true; kalau dibiarkan, memotongnya paksa dengan
// stopAllMotifs membuat parameter terakhir yang ia tulis membeku -- air matanya
// tetap mengalir terus. Dengan loop dimatikan (bawaan), motion selesai sendiri,
// memudar, dan parameter kembali ke default.
const isiSumber = await readdir(SUMBER);
/** @type {{grup: string, file: string}[]} */
const dipasang = [];
for (const g of konfig.gerakan) {
  const namaSumber = [g.sumber, basename(g.berkas)].filter(Boolean).find((f) => isiSumber.includes(f));
  if (!namaSumber) {
    console.warn(
      `  LEWAT  ${g.nama}: tidak menemukan ${[g.sumber, basename(g.berkas)].join(' / ')} di ${SUMBER}`,
    );
    continue;
  }
  const json = JSON.parse(await readFile(join(SUMBER, namaSumber), 'utf8'));
  if (json.Meta && !g.ulang) json.Meta.Loop = false;
  await tulis(g.berkas, JSON.stringify(json, null, 2) + '\n');
  dipasang.push({ grup: g.grup, file: g.berkas });
}
/** @type {Record<string, {File: string}[]>} */
const Motions = {};
for (const p of dipasang) (Motions[p.grup] ??= []).push({ File: p.file });

// Label cdi3 dialihbahasakan; Id + GroupId dibiarkan.
const berkasCdi = JSON.parse(await readFile(join(SUMBER, cdi), 'utf8'));
for (const p of berkasCdi.Parameters) {
  if (LABEL[p.Id]) {
    p.Name = LABEL[p.Id];
    continue;
  }
  for (const [dari, ke] of KAMUS) p.Name = p.Name.split(dari).join(ke);
  p.Name = p.Name.replace(/\s+/g, ' ').trim();
}
await tulis(`${NAMA}.cdi3.json`, JSON.stringify(berkasCdi, null, 2) + '\n');

for (const e of semuaEkspresi) {
  await tulis(
    `ekspresi/${e.nama}.exp3.json`,
    JSON.stringify(ekspresiKeJson(e, konfig.pudarDetik), null, 2) + '\n',
  );
}

await tulis(
  `${NAMA}.model3.json`,
  JSON.stringify(
    {
      Version: 3,
      FileReferences: {
        Moc: `${NAMA}.moc3`,
        Textures: tekstur.map((t) => `tekstur/${t}`),
        Physics: `${NAMA}.physics3.json`,
        DisplayInfo: `${NAMA}.cdi3.json`,
        Expressions: semuaEkspresi.map((e) => ({ Name: e.nama, File: `ekspresi/${e.nama}.exp3.json` })),
        // Sengaja BUKAN grup "Idle": pustaka mematikan kedip otomatis begitu ada
        // motion yang berjalan, dan napas/goyang kepala sudah disetel di dalamnya.
        Motions,
      },
      Groups: [
        { Target: 'Parameter', Name: 'EyeBlink', Ids: ['ParamEyeLOpen', 'ParamEyeROpen'] },
        { Target: 'Parameter', Name: 'LipSync', Ids: ['ParamMouthOpenY'] },
      ],
    },
    null,
    2,
  ) + '\n',
);

const sisa = berkasCdi.Parameters.filter((p) => /[^\x00-\x7F]/.test(p.Name));
console.log(
  `selesai -> ${TUJUAN}\n  ${tekstur.length} tekstur (${folderTekstur}), ` +
    `${konfig.wajah.length} wajah + ${konfig.pose.length} pose, ${dipasang.length} gerakan`,
);
for (const p of konfig.peringatan) console.warn(`  PERINGATAN ${p}`);
