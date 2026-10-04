import { defineComponent, nextTick, ref, watch } from "vue";
const DaftarPesan = defineComponent({
  name: "DaftarPesan",
  props: { pesan: { type: Array, required: true } },
  setup(props) {
    const wadah = ref();
    watch(
      // Sidik jari murah: berubah saat ada pesan baru atau teks bertambah.
      () => props.pesan.map((m) => `${m.id}:${m.content.length}`).join(","),
      async () => {
        await nextTick();
        wadah.value?.scrollTo({ top: wadah.value.scrollHeight, behavior: "smooth" });
      }
    );
    return () => <div ref={wadah} class="messages" aria-live="polite">
        {!props.pesan.length && <div class="empty">
            <span>01</span>
            <h2>Link terenkripsi siap.</h2>
            <p>Ketik pesan. Semua inferensi tetap berjalan di mesin lokal.</p>
          </div>}
        {props.pesan.map((message) => <article key={message.id} class={["message", message.role, { error: message.error }]}>
            <div class="meta">{message.role === "user" ? "MASTER" : "SILVER WOLF"} <time>#{String(message.id).padStart(3, "0")}</time></div>
            <p>{message.content}{message.pending && <i class="cursor" />}</p>
          </article>)}
      </div>;
  }
});
export {
  DaftarPesan
};
