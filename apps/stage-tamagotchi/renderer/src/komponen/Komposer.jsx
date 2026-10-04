import { defineComponent } from "vue";
const Komposer = defineComponent({
  name: "Komposer",
  props: {
    nilai: { type: String, required: true },
    terkirim: { type: Boolean, required: true },
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
    const saatKirim = (event) => {
      event.preventDefault();
      props.kirim();
    };
    const saatTombol = (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.ctrlKey && !event.altKey && !event.metaKey) {
        event.preventDefault();
        props.kirim();
      }
    };
    return () => <form class="composer" onSubmit={saatKirim}>
        <div class="compose-head">
          <label for="message">TRANSMISI BARU</label>
          <div class="audio-controls">
            <button
      type="button"
      class={["tool", { active: props.merekam }]}
      disabled={props.sibukAudio}
      onClick={() => props.rekam()}
    >
              {props.merekam ? "\u25A0 STOP" : "\u25CF MIC"}
            </button>
            <button
      type="button"
      class={["tool", { active: props.suaraAktif }]}
      onClick={() => props.toggleSuara()}
    >
              ◖ SUARA
            </button>
          </div>
        </div>
        <div class="input-row">
          <textarea
      id="message"
      rows={2}
      maxlength={4e3}
      placeholder="Tulis atau rekam suara..."
      value={props.nilai}
      disabled={props.terkirim}
      onInput={(event) => props.ubah(event.target.value)}
      onKeydown={saatTombol}
    />
          <button disabled={!props.nilai.trim() || props.terkirim} aria-label="Kirim">↗</button>
        </div>
        <small>{props.status || "ENTER kirim \xB7 STT/TTS lokal"} · {props.nilai.length}/4000</small>
      </form>;
  }
});
export {
  Komposer
};
