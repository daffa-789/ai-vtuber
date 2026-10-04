function bersih(nilai) {
  const v = nilai.trim();
  if (v.length >= 2 && v[0] === v[v.length - 1] && (v[0] === '"' || v[0] === "'"))
    return v.slice(1, -1);
  return v;
}
function potongKomentar(nilai) {
  const mentah = nilai.trim();
  if (mentah.length >= 2 && (mentah[0] === '"' || mentah[0] === "'")) {
    const kutip = mentah[0];
    const akhir = mentah.indexOf(kutip, 1);
    return akhir > 0 ? mentah.slice(1, akhir) : mentah.slice(1);
  }
  for (let i = 0; i < mentah.length; i++) {
    if (mentah[i] === "#" && i > 0 && (mentah[i - 1] === " " || mentah[i - 1] === "	"))
      return mentah.slice(0, i).replace(/\s+$/, "");
  }
  return mentah;
}
function bacaEnv(isi) {
  const hasil = {};
  for (const barisMentah of isi.split(/\r?\n/)) {
    const baris = barisMentah.trim();
    if (!baris || baris.startsWith("#") || !baris.includes("="))
      continue;
    const idx = baris.indexOf("=");
    const kunci = baris.slice(0, idx).trim();
    const nilai = baris.slice(idx + 1);
    if (kunci)
      hasil[kunci] = potongKomentar(nilai);
  }
  return hasil;
}
export {
  bacaEnv,
  bersih,
  potongKomentar
};
