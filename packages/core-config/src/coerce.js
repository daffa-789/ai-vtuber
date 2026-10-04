function nilai(env, kunci, bawaan = "") {
  const dariEnv = env.environ[kunci];
  if (dariEnv !== void 0 && dariEnv.trim() !== "")
    return bersihLocal(dariEnv);
  return env.file[kunci] ?? bawaan;
}
function bersihLocal(nilai2) {
  const v = nilai2.trim();
  if (v.length >= 2 && v[0] === v[v.length - 1] && (v[0] === '"' || v[0] === "'"))
    return v.slice(1, -1);
  return v;
}
function angka(env, kunci, bawaan) {
  const mentah = String(nilai(env, kunci, String(bawaan))).trim();
  if (mentah === "")
    return bawaan;
  const n = Number(mentah);
  if (!Number.isFinite(n) || !Number.isInteger(n)) {
    env.warnings.push(`${kunci}="${mentah}" bukan bilangan bulat; dipakai bawaan ${bawaan}`);
    return bawaan;
  }
  return n;
}
function angkaFloat(env, kunci, bawaan) {
  const mentah = String(nilai(env, kunci, String(bawaan))).trim();
  if (mentah === "")
    return bawaan;
  const n = Number(mentah);
  if (!Number.isFinite(n)) {
    env.warnings.push(`${kunci}="${mentah}" bukan bilangan; dipakai bawaan ${bawaan}`);
    return bawaan;
  }
  return n;
}
const BENAR = /* @__PURE__ */ new Set(["true", "1", "ya", "on"]);
const SALAH = /* @__PURE__ */ new Set(["false", "0", "tidak", "off"]);
function bool_(env, kunci, bawaan) {
  const mentah = nilai(env, kunci, bawaan ? "true" : "false").trim().toLowerCase();
  if (BENAR.has(mentah))
    return true;
  if (SALAH.has(mentah))
    return false;
  env.warnings.push(`${kunci}="${mentah}" bukan boolean; dipakai bawaan ${bawaan}`);
  return bawaan;
}
function daftar(env, kunci, bawaan) {
  return nilai(env, kunci, bawaan).split(",").map((s) => s.trim()).filter(Boolean);
}
export {
  angka,
  angkaFloat,
  bool_,
  daftar,
  nilai
};
