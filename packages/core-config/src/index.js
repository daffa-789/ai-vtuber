import { angka, angkaFloat, bool_, daftar, nilai } from "./coerce.js";
import { AKAR, bacaEnvAkar, temukanPersona } from "./paths.js";
function buatEnvSource(akar = AKAR, environ = process.env) {
  return { file: bacaEnvAkar(akar), environ, warnings: [] };
}
function parseAvatar(env, akar, bacaMotionIndeks) {
  const wajah = [];
  const pose = [];
  const gerak = [];
  const semua = [
    ...Object.entries(env.file),
    ...Object.entries(env.environ).filter((e) => typeof e[1] === "string")
  ];
  for (const [k, v] of semua) {
    if (k.startsWith("VITE_WAJAH_"))
      wajah.push({ nama: k.replace("VITE_WAJAH_", "").toLowerCase().replace(/_/g, "-") });
    else if (k.startsWith("VITE_POSE_"))
      pose.push({ nama: k.replace("VITE_POSE_", "").toLowerCase().replace(/_/g, "-") });
    else if (k.startsWith("VITE_GERAK_")) {
      const pasangan = [...v.matchAll(/(\S+)=([^\s]+)/g)];
      const ambil = (nama) => pasangan.find((m) => m[1] === nama)?.[2] ?? "";
      const berkas = ambil("berkas");
      gerak.push({
        nama: k.replace("VITE_GERAK_", "").toLowerCase(),
        grup: ambil("grup"),
        indeks: berkas ? bacaMotionIndeks(berkas) : 0,
        ulang: v.includes("ulang=true") || v.includes("ulang=1")
      });
    }
  }
  void akar;
  return { wajah, pose, gerak };
}
function bacaKonfig(env = buatEnvSource(), akar = AKAR, bacaMotionIndeks = () => 0) {
  const tampakMentah = nilai(env, "VTUBER_TAMPAK", "pet").toLowerCase();
  const sembunyiMentah = nilai(env, "VTUBER_PET_SEMBUNYI", "layar-penuh").toLowerCase();
  const providerMentah = nilai(env, "VTUBER_LLM_PROVIDER", "local").toLowerCase();
  const localModelCtx = angka(env, "VTUBER_LOCAL_MODEL_CTX", 8192);
  const konfig2 = {
    akar,
    akarPersona: temukanPersona(akar),
    warnings: env.warnings,
    port: angka(env, "VTUBER_PORT", 8787),
    tampak: tampakMentah === "browser" ? "browser" : "pet",
    petSembunyi: sembunyiMentah === "tidak" || sembunyiMentah === "maksimal" ? sembunyiMentah : "layar-penuh",
    petTray: bool_(env, "VTUBER_PET_TRAY", true),
    petHotkey: nilai(env, "VTUBER_PET_HOTKEY", "ctrl+shift+s").toLowerCase(),
    llmProvider: ["local", "llama_cpp", "vulkan", "ollama"].includes(providerMentah) ? providerMentah : "local",
    localModelPath: nilai(env, "VTUBER_LOCAL_MODEL_PATH", ""),
    localModelThreads: angka(env, "VTUBER_LOCAL_MODEL_THREADS", 4),
    localModelCtx,
    localModelAlias: nilai(env, "VTUBER_LOCAL_MODEL_ALIAS", ""),
    localMinP: angkaFloat(env, "VTUBER_LOCAL_MIN_P", 0),
    localTopP: angkaFloat(env, "VTUBER_LOCAL_TOP_P", 0.95),
    localReasoning: ["on", "off", "auto"].includes(nilai(env, "VTUBER_LOCAL_REASONING", "off").toLowerCase()) ? nilai(env, "VTUBER_LOCAL_REASONING", "off").toLowerCase() : "off",
    llamaServer: nilai(env, "VTUBER_LLAMA_SERVER", "bin/llama"),
    vulkanNgl: angka(env, "VTUBER_VULKAN_NGL", 99),
    vulkanFa: bool_(env, "VTUBER_VULKAN_FA", true),
    // `angka(...) or LOCAL_MODEL_CTX`: 0 berarti "ikut konteks model lokal".
    vulkanCtx: angka(env, "VTUBER_VULKAN_CTX", 0) || localModelCtx,
    vulkanPerangkat: nilai(env, "VTUBER_VULKAN_PERANGKAT", "Vulkan0"),
    vulkanMuatBoot: bool_(env, "VTUBER_VULKAN_MUAT_BOOT", true),
    vulkanSlotDiam: bool_(env, "VTUBER_VULKAN_SLOT_DIAM", true),
    ollamaUrl: nilai(env, "VTUBER_OLLAMA_URL", "http://127.0.0.1:11434"),
    ollamaModel: nilai(env, "VTUBER_OLLAMA_MODEL", "llama3.2:3b"),
    sttHidup: bool_(env, "VTUBER_STT", true),
    sttModel: nilai(env, "VTUBER_STT_MODEL", "base"),
    sttModelPath: nilai(env, "VTUBER_STT_MODEL_PATH", "assets/whisper"),
    sttBahasa: nilai(env, "VTUBER_STT_BAHASA", "id"),
    sttKomputasi: nilai(env, "VTUBER_STT_KOMPUTASI", "int8"),
    sttThreads: angka(env, "VTUBER_STT_THREADS", 2),
    sttBeam: angka(env, "VTUBER_STT_BEAM", 1),
    sttMuatBoot: bool_(env, "VTUBER_STT_MUAT_BOOT", false),
    sttMaksDetik: angka(env, "VTUBER_STT_MAKS_DETIK", 30),
    jedaFakta: angka(env, "VTUBER_JEDA_FAKTA", 8),
    ttsRantai: daftar(env, "VTUBER_TTS_RANTAI", "piper+rvc,piper"),
    ttsBatasaDetik: angka(env, "VTUBER_TTS_BATAS_DETIK", 20),
    ttsJedaResep: angka(env, "VTUBER_TTS_JEDA_RESEP", 60),
    ttsPerKalimat: bool_(env, "VTUBER_TTS_PER_KALIMAT", true),
    piperModel: nilai(env, "VTUBER_TTS_PIPER_MODEL", "assets/piper/id_ID-news_tts-medium.onnx"),
    piperSuara: nilai(env, "VTUBER_TTS_PIPER_SUARA", "id_ID-news_tts-medium"),
    piperVolume: angka(env, "VTUBER_TTS_PIPER_VOLUME", 100),
    piperPanjang: angkaFloat(env, "VTUBER_TTS_PIPER_PANJANG", 1),
    piperNoise: angkaFloat(env, "VTUBER_TTS_PIPER_NOISE", 0.667),
    piperNoiseW: angkaFloat(env, "VTUBER_TTS_PIPER_NOISE_W", 0.8),
    rvcHidup: bool_(env, "VTUBER_RVC", true),
    rvcFolder: nilai(env, "VTUBER_RVC_FOLDER", "assets/rvc"),
    rvcModel: nilai(env, "VTUBER_RVC_MODEL", "furina"),
    rvcIndeks: nilai(env, "VTUBER_RVC_INDEKS", ""),
    rvcVersi: nilai(env, "VTUBER_RVC_VERSI", "v2"),
    rvcF0: nilai(env, "VTUBER_RVC_F0", "pm"),
    rvcTranspose: angka(env, "VTUBER_RVC_TRANSPOSE", 0),
    rvcIndeksLaju: angkaFloat(env, "VTUBER_RVC_INDEKS_LAJU", 0),
    rvcProteksi: angkaFloat(env, "VTUBER_RVC_PROTEKSI", 0.33),
    rvcPencucian: angka(env, "VTUBER_RVC_PENCUCIAN", 3),
    rvcCampurRms: angkaFloat(env, "VTUBER_RVC_CAMPUR_RMS", 1),
    rvcResample: angka(env, "VTUBER_RVC_RESAMPLE", 0),
    rvcMuatBoot: bool_(env, "VTUBER_RVC_MUAT_BOOT", false),
    rvcBatasAntrean: angka(env, "VTUBER_RVC_BATAS_ANTREAN", 8),
    ttsCache: bool_(env, "VTUBER_TTS_CACHE", true),
    ttsCacheFolder: nilai(env, "VTUBER_TTS_CACHE_FOLDER", "var/cache-suara"),
    ttsCacheMaksMb: angka(env, "VTUBER_TTS_CACHE_MAKS_MB", 250),
    ttsMeterik: bool_(env, "VTUBER_TTS_METERIK", false),
    ...parseAvatar(env, akar, bacaMotionIndeks),
    stub: bool_(env, "VTUBER_STUB", false),
    maksPesan: 24,
    maksKarakter: 4e3,
    maksBody: 64 * 1024,
    maksAudio: 2 * 1024 * 1024
  };
  return konfig2;
}
let _cache;
function konfig() {
  _cache ??= bacaKonfig();
  return _cache;
}
import { AKAR as AKAR2, AKAR_PERSONA, bacaEnvAkar as bacaEnvAkar2, dariAkar, temukanPersona as temukanPersona2 } from "./paths.js";
import { angka as angka2, angkaFloat as angkaFloat2, bool_ as bool_2, daftar as daftar2, nilai as nilai2 } from "./coerce.js";
import { bacaEnv, bersih, potongKomentar } from "./env-file.js";
export {
  AKAR2 as AKAR,
  AKAR_PERSONA,
  angka2 as angka,
  angkaFloat2 as angkaFloat,
  bacaEnv,
  bacaEnvAkar2 as bacaEnvAkar,
  bacaKonfig,
  bersih,
  bool_2 as bool_,
  buatEnvSource,
  daftar2 as daftar,
  dariAkar,
  konfig,
  nilai2 as nilai,
  parseAvatar,
  potongKomentar,
  temukanPersona2 as temukanPersona
};
