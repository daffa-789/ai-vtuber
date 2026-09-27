/**
 * Mode tampilan: browser (panel lengkap) atau pet (melayang di desktop).
 *
 * Ditentukan dari URL: pywebview membuka `/?tampak=pet`, browser biasa membuka `/`.
 * Satu halaman, dua wujud -- sengaja, supaya kontrak DOM yang dipakai chat.js dan
 * main.js (#log, #isi, #btn-mic, #stage, ...) tidak bercabang jadi dua sumber
 * kebenaran yang bisa berbeda diam-diam.
 *
 * Panggil pasangTampil() SEBELUM PIXI.Application dibuat: ia menulis
 * `html[data-tampak]`, dan CSS mode pet mengubah kanvas mengisi jendela. Kalau
 * dipanggil setelahnya, kanvas dibuat dengan ukuran lama lalu tidak pernah ikut.
 */

export function modeTampil() {
  try {
    return new URLSearchParams(location.search).get('tampak') === 'pet' ? 'pet' : 'browser';
  } catch {
    return 'browser';
  }
}

/** @returns {'pet'|'browser'} mode yang aktif */
export function pasangTampil() {
  const mode = modeTampil();
  if (mode !== 'pet') {
    // Mode browser tidak punya kotak obrolan yang bisa disembunyikan; hotkey
    // global tetap memanggil nama ini, jadi ia harus ADA dan menjawab dengan jujur
    // -- bukan melempar, karena lemparannya muncul sebagai galat di log Python
    // yang sama sekali tidak ada hubungannya dengan penyebabnya.
    window.__vtuberPanel = () => false;
    return mode;
  }

  const html = document.documentElement;
  html.dataset.tampak = 'pet';

  const panelTerbuka = () => document.body.classList.contains('panel-terbuka');
  const ubahPanel = (buka) => document.body.classList.toggle('panel-terbuka', buka);

  const fokusIsi = () => {
    const isi = document.getElementById('isi');
    if (isi) setTimeout(() => isi.focus(), 30);
  };

  /**
   * Satu-satunya pintu untuk membuka/menutup kotak obrolan, dipakai bersama oleh
   * klik kanan (di bawah) dan hotkey global dari Python (lewat evaluate_js).
   * Sengaja satu pintu: dua jalur yang menulis keadaan yang sama adalah cara
   * tercepat membuat keduanya berbeda diam-diam.
   * Tanpa argumen = balikkan keadaan sekarang.
   */
  window.__vtuberPanel = (buka) => {
    ubahPanel(buka === undefined ? !panelTerbuka() : !!buka);
    if (panelTerbuka()) fokusIsi();
    return panelTerbuka();
  };

  // Klik kanan di mana saja = buka/tutup kotak obrolan. Menu bawaan WebView2
  // (Reload / View Source / Inspect) ikut hilang, yang memang diinginkan pet.
  window.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    window.__vtuberPanel();
  });

  // Esc menutup; klik di luar panel (di atas tubuhnya) juga menutup, supaya pet
  // tidak tertinggal sebagai kartu yang menempel di layar.
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && panelTerbuka()) {
      e.preventDefault();
      ubahPanel(false);
    }
  });
  document.addEventListener('pointerdown', (e) => {
    if (!panelTerbuka()) return;
    const panel = document.getElementById('panel');
    if (panel && !panel.contains(e.target)) ubahPanel(false);
  });

  return mode;
}
