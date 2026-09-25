// Pasang atau perbarui ekspresi model karakter bahasa Indonesia di public/models/penyihir.
//
// Resep wajah, pose, dan gerakan dibaca dari .env lewat web/konfigurasi.js.
// Berkas .exp3.json hasil skrip ini cuma salinan supaya alat luar (VTube Studio,
// Cubism Editor) menampilkan wajah yang sama dengan aplikasi.
//
//   node scripts/pasang-model.js [folder-sumber]
import { copyFile, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { envDariDisk } from './env.js';
import { bacaKonfigurasi, ekspresiKeJson } from '../web/konfigurasi.js';

const TUJUAN = resolve('public/models/penyihir');
const NAMA = 'penyihir';

const konfig = bacaKonfigurasi(envDariDisk());
const semuaEkspresi = [...konfig.wajah, ...konfig.pose];

const tulis = async (ke, isi) => {
  await mkdir(dirname(resolve(TUJUAN, ke)), { recursive: true });
  await writeFile(resolve(TUJUAN, ke), isi);
  console.log(`  tulis  ${ke}`);
};

// Cek apakah ada folder sumber baru yang diberikan
const argSumber = process.argv[2];
const sumberAda = argSumber && existsSync(resolve(argSumber));

if (sumberAda) {
  const SUMBER = resolve(argSumber);
  console.log(`Memasang dari sumber: ${SUMBER} -> ${TUJUAN}`);
  // Label parameter Mandarin -> Indonesia
  const LABEL = {
    Param59: 'mata bintang',
    Param60: 'mata hati',
    Param61: 'memamerkan barang 1',
    Param62: 'memamerkan barang 2',
    Param64: 'hantu kecil peliharaan',
    Param65: 'kalung',
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
    ['脸颊', 'pipi'],
    ['前发', 'poni'],
    ['侧发', 'rambut samping'],
    ['后发', 'rambut belakang'],
    ['饰品', 'aksesori'],
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

  const DIABAIKAN = ['Thumbs.db', 'items_pinned_to_model.json'];

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

  const moc = await cari(/\\.moc3$/);
  const physics = await cari(/\\.physics3\\.json$/);
  const cdi = await cari(/\\.cdi3\\.json$/);
  const akar = moc.replace(/\\.moc3$/, '');

  const kandidat = [`${akar}.${konfig.tekstur}`, konfig.tekstur].filter((f) => existsSync(join(SUMBER, f)));
  if (kandidat.length) {
    const folderTekstur = kandidat[0];
    const tekstur = (await readdir(join(SUMBER, folderTekstur))).filter(
      (f) => f.endsWith('.png') && !DIABAIKAN.includes(f),
    );
    for (const t of tekstur) await salin(`${folderTekstur}/${t}`, `tekstur/${t}`);
  }

  await salin(moc, `${NAMA}.moc3`);
  await salin(physics, `${NAMA}.physics3.json`);

  const berkasCdi = JSON.parse(await readFile(join(SUMBER, cdi), 'utf8'));
  for (const p of berkasCdi.Parameters) {
    if (LABEL[p.Id]) {
      p.Name = LABEL[p.Id];
      continue;
    }
    for (const [dari, ke] of KAMUS) p.Name = p.Name.split(dari).join(ke);
    p.Name = p.Name.replace(/\\s+/g, ' ').trim();
  }
  await tulis(`${NAMA}.cdi3.json`, JSON.stringify(berkasCdi, null, 2) + '\\n');
}

// Perbarui ekspresi .exp3.json langsung dari .env ke public/models/penyihir
for (const e of semuaEkspresi) {
  await tulis(
    `ekspresi/${e.nama}.exp3.json`,
    JSON.stringify(ekspresiKeJson(e, konfig.pudarDetik), null, 2) + '\n',
  );
}

// Temukan tekstur yang ada di TUJUAN/tekstur
const folderTekstur = join(TUJUAN, 'tekstur');
const daftarTekstur = existsSync(folderTekstur)
  ? (await readdir(folderTekstur)).filter((f) => f.endsWith('.png'))
  : ['texture_00.png', 'texture_01.png'];

/** @type {Record<string, {File: string}[]>} */
const Motions = {};
for (const g of konfig.gerakan) {
  (Motions[g.grup] ??= []).push({ File: g.berkas });
}

await tulis(
  `${NAMA}.model3.json`,
  JSON.stringify(
    {
      Version: 3,
      FileReferences: {
        Moc: `${NAMA}.moc3`,
        Textures: daftarTekstur.map((t) => `tekstur/${t}`),
        Physics: `${NAMA}.physics3.json`,
        DisplayInfo: `${NAMA}.cdi3.json`,
        Expressions: semuaEkspresi.map((e) => ({ Name: e.nama, File: `ekspresi/${e.nama}.exp3.json` })),
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

console.log(`\nSelesai -> ${TUJUAN}\n  ${konfig.wajah.length} wajah + ${konfig.pose.length} pose terpasang.`);
