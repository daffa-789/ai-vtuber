import { Application, Ticker } from "pixi.js";
import { Live2DModel } from "pixi-live2d-display/cubism4";
import { bacaPanggung, hitungSkala } from "./panggung.js";
class Live2DRenderer {
  app;
  opsi;
  pas;
  model;
  constructor(canvas, opsi = {}) {
    this.opsi = { ...bacaPanggung(), ...opsi };
    Live2DModel.registerTicker(Ticker);
    const resolution = Math.min(globalThis.devicePixelRatio || 1, this.opsi.skalaMaks);
    this.app = new Application({
      view: canvas,
      resizeTo: canvas.parentElement ?? window,
      backgroundAlpha: 0,
      antialias: true,
      autoDensity: true,
      resolution
    });
    this.pas = () => this.paskan();
    this.app.renderer.on("resize", this.pas);
    window.addEventListener("resize", this.pas);
  }
  async load(url) {
    const model = await Live2DModel.from(url, { autoInteract: false });
    this.model = model;
    this.app.stage.addChild(model);
    this.paskan();
  }
  /**
   * Hitung skala karakter.
   *
   * KUNCI PERBAIKAN: ukuran dasar diambil dari `internalModel`, BUKAN
   * `model.width`. Getter `width` PIXI v6 adalah `scale.x * getLocalBounds().width`
   * -- artinya nilainya ikut berubah oleh skala yang sedang kita hitung, sehingga
   * `fit()` versi lama tidak idempoten: s1 = K (pas), s2 = K/s1 = 1 (ukuran
   * native model, jauh lebih besar dari jendela), s3 = K, dan seterusnya.
   * `internalModel.width` adalah `originalWidth * localTransform.a`, tetap
   * terhadap `model.scale`, jadi aman dipanggil berulang kali.
   */
  paskan() {
    const model = this.model;
    if (!model) return;
    const dasar = model.internalModel;
    if (!dasar?.width || !dasar?.height) return;
    const { width: W, height: H } = this.app.screen;
    if (!W || !H) return;
    const scale = hitungSkala(W, H, dasar.width, dasar.height, this.opsi.zoom);
    if (!scale) return;
    model.scale.set(scale);
    model.anchor.set(this.opsi.x, this.opsi.jangkar);
    model.x = W * this.opsi.x;
    model.y = H * this.opsi.jangkar;
  }
  setExpression(name) {
    void this.model?.expression(name);
  }
  setPose(_name, _on) {
  }
  async startMotion(group, index, priority = 2) {
    return Boolean(await this.model?.motion(group, index, priority));
  }
  setMouth(level) {
    const core = this.model?.internalModel.coreModel;
    core?.setParameterValueById?.("ParamMouthOpenY", Math.max(0, Math.min(1, level)));
  }
  destroy() {
    window.removeEventListener("resize", this.pas);
    this.app.renderer.off("resize", this.pas);
    this.model?.destroy();
    this.app.destroy(false, { children: true, texture: true, baseTexture: true });
  }
}
export {
  Live2DRenderer,
  bacaPanggung,
  hitungSkala
};
