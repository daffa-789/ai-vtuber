// Kebijakan memori: apa yang masuk prompt, bagaimana mood bergeser, dan kapan
// fakta baru diekstrak. Sengaja tidak menyentuh filesystem -- itu urusan obsidian.mjs.

const NILAI_TAG = {
  senyum: 0.25,
  semangat: 0.35,
  goda: 0.2,
  netral: 0,
  bingung: -0.05,
  kaget: 0,
  lelah: -0.2,
  sedih: -0.3,
  sebal: -0.25,
};

const jepit = (n, min, maks) => Math.min(maks, Math.max(min, n));

export const MOOD_AWAL = { valensi: 0.2, energi: 0.6, afinitas: 0.3, pertukaran: 0 };

/** Mood bergeser dari tag yang dia pakai sendiri -- tanpa panggilan API tambahan. */
export function perbaruiMood(lama, tag) {
  const dasar = lama ?? MOOD_AWAL;
  const delta = NILAI_TAG[tag] ?? 0;
  return {
    valensi: jepit(dasar.valensi * 0.8 + delta * 0.5, -1, 1),
    energi: jepit(dasar.energi * 0.95 + (tag === 'semangat' ? 0.1 : 0) - 0.02, 0, 1),
    afinitas: jepit(dasar.afinitas + 0.03, 0, 1),
    pertukaran: (dasar.pertukaran ?? 0) + 1,
    alasan: `tag terakhir: ${tag ?? 'tidak ada'}`,
  };
}

function suasanaku(mood) {
  if (!mood) return '';
  if (mood.valensi < -0.25) return 'Kamu lagi agak berat hari ini, jadi jawabanmu lebih pendek dan lebih jujur.';
  if (mood.valensi > 0.3 && mood.energi > 0.5) return 'Kamu lagi ceria, boleh lebih usil sedikit.';
  if (mood.energi < 0.3) return 'Kamu lagi capek, bicaranya lebih pelan dan pendek.';
  return '';
}

/** Perakitan system instruction: persona + yang dia ingat + suasananya sekarang. */
export function gabungSystem(persona, fakta, mood) {
  const bagian = [persona];
  if (fakta?.length) {
    bagian.push(`## Yang aku ingat tentang Master\n${fakta.map((f) => `- ${f}`).join('\n')}`);
  }
  if (mood) {
    const s = suasanaku(mood);
    if (s) bagian.push(`## Suasana hatiku sekarang\n${s}`);
  }
  return bagian.join('\n\n');
}

/**
 * Ekstraksi fakta memakai model yang sama, jadi hanya menambah satu panggilan
 * dan itu pun jarang: pemanggilnya menyetel kapan ini layak dijalankan.
 */
export async function ekstrakFakta(ai, model, percakapan, faktaLama) {
  const instruksi = [
    'Dari percakapan di bawah, tuliskan FAKTA BARU yang layak diingat lama tentang Master:',
    'pekerjaan, kebiasaan, orang, tanggal, preferensi, proyek, kondisi hari ini.',
    'Abaikan basa-basi dan hal yang sudah ada di daftar fakta lama.',
    'Balas HANYA array JSON berisi string pendek berbahasa Indonesia. [] kalau tidak ada.',
    '',
    `Fakta lama: ${JSON.stringify(faktaLama)}`,
    '',
    'Percakapan:',
    percakapan.map((m) => `${m.role === 'user' ? 'Master' : 'Haru'}: ${m.content}`).join('\n'),
  ].join('\n');

  const r = await ai.models.generateContent({
    model,
    contents: instruksi,
    config: { generationConfig: { temperature: 0, maxOutputTokens: 500 } },
  });

  const teks = (r.text ?? '').replace(/^[^\[]*/, '').replace(/[^\]]*$/, '');
  const hasil = JSON.parse(teks);
  return Array.isArray(hasil) ? hasil.filter((f) => typeof f === 'string' && f.trim()).map((f) => f.trim()) : [];
}
