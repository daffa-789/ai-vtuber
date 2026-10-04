import { defineComponent } from "vue";
const Panggung = defineComponent({
  name: "Panggung",
  props: {
    kanvas: { type: Object, required: true },
    modelHilang: { type: Boolean, required: true },
    ekspresi: { type: String, required: true }
  },
  setup(props) {
    return () => <section class="stage" aria-label="Panggung Silver Wolf">
        <header class="brand">
          <span class="sigil">SW</span>
          <div><b>SILVER WOLF</b><small>STELLARON // LOCAL LINK</small></div>
        </header>
        <div class="stage-hud" />
        <canvas ref={props.kanvas} class={{ hidden: props.modelHilang }} />
        {props.modelHilang && <div class="avatar-fallback" aria-label="Model Live2D belum dipasang">
            <div class="glitch" data-text="404">404</div>
            <strong>MODEL OFFLINE</strong>
            <span>Pasang aset Live2D di public/models/silverwolf</span>
          </div>}
        <div class="expression"><span>EMOSI // RAUT</span><b>{props.ekspresi}</b></div>
      </section>;
  }
});
export {
  Panggung
};
