import { defineComponent, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useCompanionStore } from "@silverwolf/stage-ui";
import { MicrophoneRecorder, WhisperTranscriber } from "@silverwolf/audio";
import { AntreanSuara, BrowserVoicePipeline } from "@silverwolf/pipelines-audio";
import { bacaTagAwal } from "@silverwolf/core-character/tags.js";
import { bacaPanggung } from "@silverwolf/stage-ui-live2d/panggung.js";
import { Panggung } from "./komponen/Panggung.jsx";
import { Konsol } from "./komponen/Konsol.jsx";
import { lewatiTag } from "./ucapan.js";
const MODEL_URL = import.meta.env.VITE_MODEL_URL || "/models/silverwolf/silverwolf.model3.json";
const RVC_TRANSPOSE = Number(import.meta.env.VITE_RVC_TRANSPOSE ?? 9);
var stdin_default = defineComponent({
  name: "SilverWolfApp",
  setup() {
    const panggung = bacaPanggung();
    const store = useCompanionStore();
    const input = ref("");
    const kanvas = ref();
    const modelState = ref("loading");
    const recording = ref(false);
    const audioBusy = ref(false);
    const audioStatus = ref("");
    const voiceEnabled = ref(true);
    const recorder = new MicrophoneRecorder();
    const whisper = new WhisperTranscriber({
      language: "indonesian",
      onProgress: (p) => {
        if (p.progress) audioStatus.value = `Whisper ${Math.round(p.progress)}%`;
      }
    });
    let voice;
    let antrean;
    let renderer;
    function suara() {
      voice ??= new BrowserVoicePipeline({
        rvc: { contentVecUrl: "/assets/encoders/vec-768-layer-12.onnx", modelUrl: "/assets/voices/silverwolf/model.onnx", transpose: RVC_TRANSPOSE }
      });
      return voice;
    }
    onMounted(async () => {
      void store.checkHealth();
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
          audioStatus.value = error instanceof Error ? error.message : String(error);
        }
      });
      antrean = antrian;
      let mentah = "";
      let tagSelesai = false;
      let diproses = 0;
      const proses = () => {
        const pos = lewatiTag(mentah);
        if (!tagSelesai) {
          if (pos < 0) return;
          tagSelesai = true;
          const tag = bacaTagAwal(mentah);
          if (tag) store.expression = tag;
        }
        const bisaUcap = mentah.slice(Math.max(pos, 0));
        const baru = bisaUcap.slice(diproses);
        if (!baru) return;
        diproses = bisaUcap.length;
        antrian.tambah(baru);
      };
      audioBusy.value = true;
      try {
        await store.send(value, { onDelta: (potongan) => {
          mentah += potongan;
          proses();
        } });
        proses();
        antrian.tutup();
        await antrian.tungguSelesai();
      } finally {
        audioBusy.value = false;
        antrean = void 0;
      }
    }
    async function toggleMic() {
      if (audioBusy.value) return;
      if (!recording.value) {
        try {
          await recorder.start();
          recording.value = true;
          audioStatus.value = "Merekam...";
        } catch (e) {
          audioStatus.value = e instanceof Error ? e.message : String(e);
        }
        return;
      }
      recording.value = false;
      audioBusy.value = true;
      audioStatus.value = "Mengenali suara...";
      try {
        input.value = await whisper.transcribe(await recorder.stop());
        audioStatus.value = "Transkripsi siap";
      } catch (e) {
        audioStatus.value = e instanceof Error ? e.message : String(e);
      } finally {
        audioBusy.value = false;
      }
    }
    return () => <main class="shell">
        <Panggung kanvas={kanvas} modelHilang={modelState.value === "missing"} ekspresi={store.expression} />
        <Konsol
      nilai={input.value}
      merekam={recording.value}
      sibukAudio={audioBusy.value}
      status={audioStatus.value}
      suaraAktif={voiceEnabled.value}
      ubah={(nilai) => {
        input.value = nilai;
      }}
      kirim={() => void submit()}
      rekam={() => void toggleMic()}
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
