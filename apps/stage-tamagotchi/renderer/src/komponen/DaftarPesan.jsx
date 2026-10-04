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
            <div class="empty-badge">⚡ STELLARON LINK // ENCRYPTED SESSION</div>
            <h2>Halo Master, ada misi apa hari ini?</h2>
            <p>Ketik pesan atau rekam suara. Seluruh inferensi AI berjalan 100% lokal di GPU Anda melalui Vulkan.</p>
          </div>}
        {props.pesan.map((message) => <article key={message.id} class={["message", message.role, { error: message.error }]}>
            <div class="meta">
              <span>{message.role === "user" ? "👤 MASTER" : "👾 SILVER WOLF"}</span>
              <time>#{String(message.id).padStart(3, "0")}</time>
            </div>
            <p>{message.content}{message.pending && <i class="cursor" />}</p>
          </article>)}
      </div>;
  }
});
export {
  DaftarPesan
};
