import { EMOTION_TAGS, suasana } from "./mood.js";
function ringkasPersona(teks, batas = 18e3) {
  if (teks.length <= batas) return { teks, terpotong: false, bagianHilang: [] };
  let hasil = teks.slice(0, batas);
  const paragraf = hasil.lastIndexOf("\n\n");
  if (paragraf > batas / 2) hasil = hasil.slice(0, paragraf);
  const judul = [...teks.matchAll(/^## (.+)$/gm)].map((m) => m[1]?.trim()).filter((x) => Boolean(x));
  return { teks: hasil, terpotong: true, bagianHilang: judul.filter((j) => !hasil.includes(`## ${j}`)) };
}
function gabungSystem(persona, fakta, mood, lokal = true) {
  const bagian = [ringkasPersona(persona).teks];
  if (lokal) {
    bagian.push(`WAJIB: Awali setiap balasanmu dengan satu tag emosi di paling depan, persis satu dari ${EMOTION_TAGS.map((t) => `[${t}]`).join(", ")}. Contoh: [senyum] Beres, Master. Tinggal bilang bagian mana yang macet.`);
  }
  if (fakta.length) {
    const daftar = lokal ? fakta.slice(-5) : fakta;
    bagian.push(`${lokal ? "Fakta tentang Master" : "## Yang aku ingat tentang Master"}:
${daftar.map((f) => `- ${f}`).join("\n")}`);
  }
  const kini = suasana(mood);
  if (kini) bagian.push(`${lokal ? "Suasana hatimu saat ini" : "## Suasana hatiku sekarang"}: ${kini}`);
  return bagian.join("\n\n");
}
export {
  gabungSystem,
  ringkasPersona
};
