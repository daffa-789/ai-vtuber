import { EMOTION_TAGS } from "./mood.js";
const dikenal = new Set(EMOTION_TAGS);
const TAG_AWAL = /^[\s`'"]*\[{1,2}([a-zA-Z][^\n[\]{}]{0,25})\]\]*[\s`'"]*/;
const TAG_ASING = /^[\s`'"]*\[{1,2}([a-zA-Z][\w:-]{0,24})\]\]*[\s`'"]*/;
function bacaTagAwal(teks) {
  const tag = TAG_AWAL.exec(teks)?.[1]?.trim().toLowerCase();
  return tag && dikenal.has(tag) ? tag : void 0;
}
function bersihkanTagAwal(teks) {
  const tag = bacaTagAwal(teks);
  if (tag) return { teks: teks.replace(TAG_AWAL, ""), tag };
  const asing = TAG_ASING.test(teks);
  return asing ? { teks: teks.replace(TAG_ASING, "") } : { teks };
}
export {
  bacaTagAwal,
  bersihkanTagAwal
};
