import { defineComponent, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useCompanionStore } from "@silverwolf/stage-ui";
import { AntreanSuara, BrowserVoicePipeline, dapatkanAudioContext } from "@silverwolf/pipelines-audio";
import { bacaTagAwal } from "@silverwolf/core-character/tags.js";
import { bacaPanggung } from "@silverwolf/stage-ui-live2d/panggung.js";
import { Panggung } from "./komponen/Panggung.jsx";
import { Konsol } from "./komponen/Konsol.jsx";
import { lewatiTag } from "./ucapan.js";
const MODEL_URL = import.meta.env.VITE_MODEL_URL || "/models/silverwolf/silverwolf.model3.json";
var stdin_default = defineComponent({
  name: "SilverWolfApp",
  setup() {
    const panggung = bacaPanggung();
    const store = useCompanionStore();
    const input = ref("");
    const kanvas = ref();
    const modelState = ref("loading");
    const audioBusy = ref(false);
    const audioStatus = ref("");
    const voiceEnabled = ref(true);
    let voice;
    let antrean;
    let renderer;
    let lepasKunciAudio;

    function suara() {
      voice ??= new BrowserVoicePipeline({
        piper: {
          modelUrl: "/assets/piper/id_ID-news_tts-medium.onnx",
          configUrl: "/assets/piper/id_ID-news_tts-medium.onnx.json"
        }
      });
      return voice;
    }
    onMounted(async () => {
      store.startPolling();

      const bukaKunciAudio = () => {
        const ctx = dapatkanAudioContext();
        if (ctx && ctx.state === "suspended") {
          void ctx.resume().catch(() => {});
        }
      };
      window.addEventListener("pointerdown", bukaKunciAudio, { passive: true });
      window.addEventListener("keydown", bukaKunciAudio, { passive: true });
      lepasKunciAudio = () => {
        window.removeEventListener("pointerdown", bukaKunciAudio);
        window.removeEventListener("keydown", bukaKunciAudio);
      };

      // Pre-warm Piper TTS model & phonemizer di latar belakang
      void suara().create?.().then(() => {
        console.log("[App] Piper TTS siap digunakan.");
      }).catch((err) => {
        console.warn("[App] Pre-warm Piper TTS gagal:", err);
      });

      if (!kanvas.value) return;
      try {
        const { Live2DRenderer } = await import("@silverwolf/stage-ui-live2d");
        renderer = new Live2DRenderer(kanvas.value, panggung);
        await renderer.load(MODEL_URL);
        await renderer.startMotion("isyarat", 2, 1);
        modelState.value = "ready";
      } catch (error) {
        console.warn("Live2D belum tersedia:", error);
        modelState.value = "missing";
        renderer?.destroy();
        renderer = void 0;
      }
    });
    onBeforeUnmount(() => {
      lepasKunciAudio?.();
      store.stopPolling();
      antrean?.berhenti();
      renderer?.destroy();
      voice?.destroy();
    });
    watch(() => store.expression, (value) => renderer?.setExpression(value));
    async function submit() {
      const value = input.value;
      input.value = "";
      if (!voiceEnabled.value) {
        await store.send(value);
        return;
      }
      antrean?.berhenti();
      const antrian = new AntreanSuara({
        synthesize: (teks) => suara().synthesize(teks),
        onMulut: (level) => renderer?.setMouth(level),
        onKalimatMulai: () => {
          audioStatus.value = "Suara aktif";
        },
        onGalat: (error) => {
          console.warn("Kesalahan sintesis suara:", error);
          audioStatus.value = error instanceof Error ? error.message : String(error);
        }
      });
      antrean = antrian;
      let mentah = "";
      let tagSelesai = false;
      let diproses = 0;
      const proses = (selesai = false) => {
        let pos = lewatiTag(mentah);
        if (!tagSelesai) {
          if (pos < 0 && !selesai) return;
          tagSelesai = true;
          if (pos >= 0) {
            const tag = bacaTagAwal(mentah);
            if (tag) store.expression = tag;
          } else {
            pos = 0;
          }
        }
        const bisaUcap = mentah.slice(Math.max(pos, 0));
        const baru = bisaUcap.slice(diproses);
        if (!baru) return;
        diproses = bisaUcap.length;
        antrian.tambah(baru);
      };
      audioBusy.value = true;
      audioStatus.value = "Menghubungkan transmisi...";
      try {
        await store.send(value, {
          onDelta: (potongan) => {
            mentah += potongan;
            proses(false);
          }
        });
        proses(true);
        antrian.tutup();
        await antrian.tungguSelesai();
      } finally {
        audioBusy.value = false;
        antrean = void 0;
        audioStatus.value = "";
      }
    }
    return () => <main class="shell">
        <Panggung kanvas={kanvas} modelHilang={modelState.value === "missing"} ekspresi={store.expression} />
        <Konsol
      nilai={input.value}
      sibukAudio={audioBusy.value}
      status={audioStatus.value}
      suaraAktif={voiceEnabled.value}
      ubah={(nilai) => {
        input.value = nilai;
      }}
      kirim={() => void submit()}
      toggleSuara={() => {
        voiceEnabled.value = !voiceEnabled.value;
      }}
    />
      </main>;
  }
});
export {
  stdin_default as default
};
