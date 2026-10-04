function angka(value, bawaan) {
  if (value === void 0 || value.trim() === "") return bawaan;
  const n = Number(value);
  return Number.isFinite(n) ? n : bawaan;
}
function bacaPanggung(env = import.meta.env) {
  return {
    zoom: angka(env.VITE_AVATAR_ZOOM, 0.96),
    x: angka(env.VITE_AVATAR_X, 0.5),
    jangkar: angka(env.VITE_AVATAR_JANGKAR, 1),
    skalaMaks: angka(env.VITE_RENDER_SKALA_MAKS, 2)
  };
}
function hitungSkala(lebar, tinggi, dasarLebar, dasarTinggi, zoom) {
  if (!lebar || !tinggi || !dasarLebar || !dasarTinggi) return 0;
  return Math.min(lebar / dasarLebar, tinggi / dasarTinggi) * zoom;
}
export {
  bacaPanggung,
  hitungSkala
};
