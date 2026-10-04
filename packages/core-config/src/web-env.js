function envWeb(env) {
  const hasil = {};
  for (const [k, v] of Object.entries(env.file)) {
    if (k.startsWith("VITE_"))
      hasil[k] = v;
  }
  for (const [k, v] of Object.entries(env.environ)) {
    if (k.startsWith("VITE_") && typeof v === "string")
      hasil[k] = v;
  }
  return hasil;
}
export {
  envWeb
};
