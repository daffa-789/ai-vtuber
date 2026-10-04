import { defineComponent } from "vue";
import { useCompanionStore } from "@silverwolf/stage-ui";
import { DaftarPesan } from "./DaftarPesan.jsx";
import { Komposer } from "./Komposer.jsx";
const Konsol = defineComponent({
  name: "Konsol",
  props: {
    nilai: { type: String, required: true },
    merekam: { type: Boolean, required: true },
    sibukAudio: { type: Boolean, required: true },
    status: { type: String, required: true },
    suaraAktif: { type: Boolean, required: true },
    ubah: { type: Function, required: true },
    kirim: { type: Function, required: true },
    rekam: { type: Function, required: true },
    toggleSuara: { type: Function, required: true }
  },
  setup(props) {
    const store = useCompanionStore();
    return () => <section class="console">
        <header class="console-head">
          <div>
            <span class="eyebrow">STELLARON TERMINAL // PRIVATE CHANNEL</span>
            <h1>Catatan Lapangan</h1>
          </div>
          <button
            class={["status", { online: store.ready, loading: store.loading }]}
            onClick={() => void store.checkHealth()}
            title={store.healthError || store.health?.model}
          >
            <i /> {store.ready ? "VULKAN ONLINE" : store.loading ? "MEMUAT VULKAN..." : "OFFLINE"}
          </button>
        </header>

        {store.health ? (
          <div class="telemetry">
            <div class={["telemetry-chip", { loading: store.loading }]}>
              <strong>GPU:</strong> {store.health.model}
            </div>
            <div class="telemetry-chip">
              <strong>MEM:</strong> {store.health.memori}
            </div>
            <div class="telemetry-chip">
              <strong>AUDIO:</strong> Piper TTS + RVC v2
            </div>
          </div>
        ) : store.healthError ? (
          <div class="banner">Server tidak menjawab — jalankan <code>npm run dev</code></div>
        ) : null}

        <DaftarPesan pesan={store.messages} />

        <Komposer
      nilai={props.nilai}
      terkirim={store.sending}
      merekam={props.merekam}
      sibukAudio={props.sibukAudio}
      status={props.status}
      suaraAktif={props.suaraAktif}
      ubah={props.ubah}
      kirim={props.kirim}
      rekam={props.rekam}
      toggleSuara={props.toggleSuara}
    />
      </section>;
  }
});
export {
  Konsol
};
