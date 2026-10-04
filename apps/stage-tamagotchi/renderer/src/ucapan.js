function lewatiTag(teks) {
  const depan = teks.replace(/^[\s`'"]*/, "");
  if (!depan) return -1;
  if (depan[0] !== "[") return 0;
  const tutup = depan.indexOf("]");
  if (tutup < 0) return -1;
  return teks.length - depan.length + tutup + 1;
}
export {
  lewatiTag
};
