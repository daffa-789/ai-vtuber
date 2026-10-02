package config

import "strings"

// Batasan ukuran yang tidak datang dari `.env` — padanan konstanta di
// `bacaKonfig()` (maksPesan, maksKarakter, maksBody, maksAudio).
const (
	MaksPesan    = 24
	MaksKarakter = 4000
	MaksBody     = 64 * 1024
	MaksAudio    = 2 * 1024 * 1024
)

// Konfig adalah konfigurasi sisi server. Padanan `Konfig` di
// `packages/core-config/src/index.ts` dan `server_py/konfig.py`.
type Konfig struct {
	Akar        string
	AKarPersona string
	Warnings    []string

	// ── wujud aplikasi ──
	Port        int
	Tampak      string // 'pet' | 'browser'
	PetSembunyi string // 'tidak' | 'layar-penuh' | 'maksimal'
	PetTray     bool
	PetHotkey   string

	// ── otak percakapan ──
	LlmProvider       string // 'local' | 'llama_cpp' | 'vulkan' | 'ollama'
	LocalModelPath    string
	LocalModelThreads int
	LocalModelCtx     int
	// LocalModelAlias adalah nama yang dilaporkan `/v1/chat/completions`;
	// kosong = turun dari nama berkas.
	LocalModelAlias string
	// LocalMinP: min_p untuk llama-server. WAJIB 0 untuk MiniCPM5: bawaan
	// llama.cpp 0,05 membuat model ini mengulang kalimat.
	LocalMinP float64
	LocalTopP float64
	// LocalReasoning: `-rea` llama-server. Kalau hidup, balasan diawali blok
	// <think> sehingga pembaca tag emosi gagal menemukan tag.
	LocalReasoning  string // 'on' | 'off' | 'auto'
	LlamaServer     string
	VulkanNgl       int
	VulkanFa        bool
	VulkanCtx       int
	VulkanPerangkat string
	VulkanMuatBoot  bool
	VulkanSlotDiam  bool
	OllamaUrl       string
	OllamaModel     string

	// ── STT ──
	SttHidup     bool
	SttModel     string
	SttModelPath string
	SttBahasa    string
	SttKomputasi string
	SttThreads   int
	SttBeam      int
	SttMuatBoot  bool
	SttMaksDetik int

	JedaFakta int

	// ── rantai suara ──
	TtsRantai     []string
	TtsBatasDetik int
	TtsJedaResep  int
	TtsPerKalimat bool

	// ── piper ──
	PiperModel   string
	PiperSuara   string
	PiperVolume  int
	PiperPanjang float64
	PiperNoise   float64
	PiperNoiseW  float64

	// ── rvc ──
	RvcHidup        bool
	RvcFolder       string
	RvcModel        string
	RvcIndeks       string
	RvcVersi        string
	RvcF0           string
	RvcTranspose    int
	RvcIndeksLaju   float64
	RvcProteksi     float64
	RvcPencucian    int
	RvcCampurRms    float64
	RvcResample     int
	RvcMuatBoot     bool
	RvcBatasAntrean int

	// ── cache ──
	TtsCache       bool
	TtsCacheFolder string
	TtsCacheMaksMb int
	TtsMeterik     bool

	// ── tiruan & batas ──
	Stub         bool
	MaksPesan    int
	MaksKarakter int
	MaksBody     int
	MaksAudio    int
}

// pilih menjepit nilai ke salah satu dari daftar yang dikenal; kalau tidak
// cocok, pakai bawaan. Padanan pola `(['a','b'].includes(x) ? x : bawaan)`.
func pilih(nilai string, dikenal []string, bawaan string) string {
	for _, k := range dikenal {
		if nilai == k {
			return nilai
		}
	}
	return bawaan
}

// BacaKonfig membangun konfigurasi lengkap dari sebuah EnvSource.
//
// Avatar (`VITE_WAJAH_*`, `VITE_POSE_*`, `VITE_GERAK_*`) sengaja TIDAK
// diparse di sisi Go: setelah jalur peramban dibuang, kunci-kunci itu dipakai
// oleh Vite pada saat build renderer (`import.meta.env.VITE_*`) dan tidak
// pernah lagi disuntikkan server ke halaman.
func BacaKonfig(env *EnvSource, akar string) *Konfig {
	localModelCtx := Angka(env, "VTUBER_LOCAL_MODEL_CTX", 8192)
	return &Konfig{
		Akar:        akar,
		AKarPersona: TemukanPersona(akar),
		Warnings:    env.Warnings,

		Port:        Angka(env, "VTUBER_PORT", 8787),
		Tampak:      pilih(strings.ToLower(Nilai(env, "VTUBER_TAMPAK", "pet")), []string{"pet", "browser"}, "pet"),
		PetSembunyi: pilih(strings.ToLower(Nilai(env, "VTUBER_PET_SEMBUNYI", "layar-penuh")), []string{"tidak", "layar-penuh", "maksimal"}, "layar-penuh"),
		PetTray:     Bool(env, "VTUBER_PET_TRAY", true),
		PetHotkey:   strings.ToLower(Nilai(env, "VTUBER_PET_HOTKEY", "ctrl+shift+s")),

		LlmProvider:       pilih(strings.ToLower(Nilai(env, "VTUBER_LLM_PROVIDER", "local")), []string{"local", "llama_cpp", "vulkan", "ollama"}, "local"),
		LocalModelPath:    Nilai(env, "VTUBER_LOCAL_MODEL_PATH", ""),
		LocalModelThreads: Angka(env, "VTUBER_LOCAL_MODEL_THREADS", 4),
		LocalModelCtx:     localModelCtx,
		LocalModelAlias:   Nilai(env, "VTUBER_LOCAL_MODEL_ALIAS", ""),
		LocalMinP:         AngkaFloat(env, "VTUBER_LOCAL_MIN_P", 0),
		LocalTopP:         AngkaFloat(env, "VTUBER_LOCAL_TOP_P", 0.95),
		LocalReasoning:    pilih(strings.ToLower(Nilai(env, "VTUBER_LOCAL_REASONING", "off")), []string{"on", "off", "auto"}, "off"),
		LlamaServer:       Nilai(env, "VTUBER_LLAMA_SERVER", "bin/llama"),
		VulkanNgl:         Angka(env, "VTUBER_VULKAN_NGL", 99),
		VulkanFa:          Bool(env, "VTUBER_VULKAN_FA", true),
		// 0 berarti "ikut konteks model lokal".
		VulkanCtx:       atau(Angka(env, "VTUBER_VULKAN_CTX", 0), localModelCtx),
		VulkanPerangkat: Nilai(env, "VTUBER_VULKAN_PERANGKAT", "Vulkan0"),
		VulkanMuatBoot:  Bool(env, "VTUBER_VULKAN_MUAT_BOOT", true),
		VulkanSlotDiam:  Bool(env, "VTUBER_VULKAN_SLOT_DIAM", true),
		OllamaUrl:       Nilai(env, "VTUBER_OLLAMA_URL", "http://127.0.0.1:11434"),
		OllamaModel:     Nilai(env, "VTUBER_OLLAMA_MODEL", "llama3.2:3b"),

		SttHidup:     Bool(env, "VTUBER_STT", true),
		SttModel:     Nilai(env, "VTUBER_STT_MODEL", "base"),
		SttModelPath: Nilai(env, "VTUBER_STT_MODEL_PATH", "aset/suara/whisper"),
		SttBahasa:    Nilai(env, "VTUBER_STT_BAHASA", "id"),
		SttKomputasi: Nilai(env, "VTUBER_STT_KOMPUTASI", "int8"),
		SttThreads:   Angka(env, "VTUBER_STT_THREADS", 2),
		SttBeam:      Angka(env, "VTUBER_STT_BEAM", 1),
		SttMuatBoot:  Bool(env, "VTUBER_STT_MUAT_BOOT", false),
		SttMaksDetik: Angka(env, "VTUBER_STT_MAKS_DETIK", 30),

		JedaFakta: Angka(env, "VTUBER_JEDA_FAKTA", 8),

		TtsRantai:     Daftar(env, "VTUBER_TTS_RANTAI", "piper+rvc,piper"),
		TtsBatasDetik: Angka(env, "VTUBER_TTS_BATAS_DETIK", 20),
		TtsJedaResep:  Angka(env, "VTUBER_TTS_JEDA_RESEP", 60),
		TtsPerKalimat: Bool(env, "VTUBER_TTS_PER_KALIMAT", true),

		PiperModel:   Nilai(env, "VTUBER_TTS_PIPER_MODEL", "aset/suara/piper/id_ID-news_tts-medium.onnx"),
		PiperSuara:   Nilai(env, "VTUBER_TTS_PIPER_SUARA", "id_ID-news_tts-medium"),
		PiperVolume:  Angka(env, "VTUBER_TTS_PIPER_VOLUME", 100),
		PiperPanjang: AngkaFloat(env, "VTUBER_TTS_PIPER_PANJANG", 1.0),
		PiperNoise:   AngkaFloat(env, "VTUBER_TTS_PIPER_NOISE", 0.667),
		PiperNoiseW:  AngkaFloat(env, "VTUBER_TTS_PIPER_NOISE_W", 0.8),

		RvcHidup:        Bool(env, "VTUBER_RVC", true),
		RvcFolder:       Nilai(env, "VTUBER_RVC_FOLDER", "aset/suara/rvc"),
		RvcModel:        Nilai(env, "VTUBER_RVC_MODEL", "furina"),
		RvcIndeks:       Nilai(env, "VTUBER_RVC_INDEKS", ""),
		RvcVersi:        Nilai(env, "VTUBER_RVC_VERSI", "v2"),
		RvcF0:           Nilai(env, "VTUBER_RVC_F0", "pm"),
		RvcTranspose:    Angka(env, "VTUBER_RVC_TRANSPOSE", 0),
		RvcIndeksLaju:   AngkaFloat(env, "VTUBER_RVC_INDEKS_LAJU", 0.0),
		RvcProteksi:     AngkaFloat(env, "VTUBER_RVC_PROTEKSI", 0.33),
		RvcPencucian:    Angka(env, "VTUBER_RVC_PENCUCIAN", 3),
		RvcCampurRms:    AngkaFloat(env, "VTUBER_RVC_CAMPUR_RMS", 1.0),
		RvcResample:     Angka(env, "VTUBER_RVC_RESAMPLE", 0),
		RvcMuatBoot:     Bool(env, "VTUBER_RVC_MUAT_BOOT", false),
		RvcBatasAntrean: Angka(env, "VTUBER_RVC_BATAS_ANTREAN", 8),

		TtsCache:       Bool(env, "VTUBER_TTS_CACHE", true),
		TtsCacheFolder: Nilai(env, "VTUBER_TTS_CACHE_FOLDER", "var/cache-suara"),
		TtsCacheMaksMb: Angka(env, "VTUBER_TTS_CACHE_MAKS_MB", 250),
		TtsMeterik:     Bool(env, "VTUBER_TTS_METERIK", false),

		Stub:         Bool(env, "VTUBER_STUB", false),
		MaksPesan:    MaksPesan,
		MaksKarakter: MaksKarakter,
		MaksBody:     MaksBody,
		MaksAudio:    MaksAudio,
	}
}

// atau mengembalikan n bila bukan nol, selain itu bawaan. Dipakai untuk
// `angka(...) or LOCAL_MODEL_CTX`.
func atau(n, bawaan int) int {
	if n == 0 {
		return bawaan
	}
	return n
}
