"""Tampal cari tetangga-terdekat tanpa faiss.search.

Kenapa perlu: index RVC milik proyek ini (`added_IVF*_Flat_nprobe_1_*_v2.index`)
membuat **faiss-cpu 1.8.0 segfault** saat `index.search()` — bahkan untuk masukan
float32 yang contiguous dan berukuran benar, jadi bukan salah pemakaian. Index
bisa dibaca dan `reconstruct_n()` jalan normal; hanya `search()` yang mati.

Solusi: ambil vektor penyimpanannya sekali (IVF*,**Flat** memang menyimpan
vektor mentah, jadi tidak ada yang hilang), lalu cari k tetangga terdekat dengan
numpy. Untuk index seukuran ini (10.647 vektor x 768 dim) itu cepat, dan
hasilnya justru lebih tepat daripada IVF dengan nprobe=1 yang hanya menelusuri
1 dari 273 klaster.

Semantik faiss ditiru persis supaya kode RVC di bawahnya tidak berubah perilaku:
  - METRIC_INNER_PRODUCT (metric_type 1): mengembalikan hasil kali titik,
    terurut MENURUN (paling mirip paling dulu).
  - METRIC_L2 (metric_type 0): mengembalikan jarak kuadrat, terurut MENAIK.

Pakai: `pasang()` sebelum rvc-python memuat index.
"""

from __future__ import annotations

import numpy as np

METRIK_L2 = 0
METRIK_IP = 1
_BARIS_PER_TAHAP = 128


class IndeksBruteForce:
    """Pengganti Index faiss dengan pencarian brute-force numpy."""

    def __init__(self, asli):
        self._asli = asli
        self.d = int(asli.d)
        self.ntotal = int(asli.ntotal)
        self.metric_type = int(getattr(asli, "metric_type", METRIK_L2))
        self.nprobe = int(getattr(asli, "nprobe", 1))
        self.is_trained = bool(getattr(asli, "is_trained", True))
        # Simpan semua vektor sebagai matriks (ntotal, d) float32.
        self._vektor = np.ascontiguousarray(
            asli.reconstruct_n(0, self.ntotal), dtype="float32"
        )

    def reconstruct_n(self, i0: int, i1: int) -> np.ndarray:
        return self._vektor[i0:i1]

    def search(self, x: np.ndarray, k: int = 1):
        q = np.ascontiguousarray(np.asarray(x, dtype="float32"))
        if q.ndim == 1:
            q = q.reshape(1, -1)
        k = max(1, min(int(k), self.ntotal))
        jarak = np.empty((q.shape[0], k), dtype="float32")
        indeks = np.empty((q.shape[0], k), dtype="int64")

        for awal in range(0, q.shape[0], _BARIS_PER_TAHAP):
            blok = q[awal : awal + _BARIS_PER_TAHAP]
            if self.metric_type == METRIK_IP:
                skor = blok @ self._vektor.T
                ambil = -skor  # terkecil = paling mirip
            else:
                # ||a-b||^2 = |a|^2 - 2 a.b + |b|^2
                skor = (
                    np.einsum("ij,ij->i", blok, blok)[:, None]
                    - 2.0 * (blok @ self._vektor.T)
                    + np.einsum("ij,ij->i", self._vektor, self._vektor)[None, :]
                )
                ambil = skor
            # argpartition lebih murah daripada argsort penuh: hanya k teratas
            # yang kemudian diurutkan. Menjaga pemakaian memori tetap kecil.
            calon = np.argpartition(ambil, k - 1, axis=1)[:, :k]
            baris = np.arange(blok.shape[0])[:, None]
            urutan = np.argsort(
                np.take_along_axis(ambil, calon, axis=1), axis=1, kind="stable"
            )
            urut = np.take_along_axis(calon, urutan, axis=1)
            indeks[awal : awal + blok.shape[0]] = urut
            jarak[awal : awal + blok.shape[0]] = np.take_along_axis(skor, urut, axis=1)

        return jarak, indeks

    def __getattr__(self, nama):
        # Apa pun yang tidak ditiru di atas diteruskan ke index asli.
        return getattr(self._asli, nama)


def pasang(log=print):
    """Ganti `faiss.read_index` supaya mengembalikan pembungkus brute-force."""
    import faiss

    if getattr(faiss.read_index, "_huohuo_tampalan", False):
        return False

    baca_asli = faiss.read_index

    def baca_berbungkus(*args, **kwargs):
        asli = baca_asli(*args, **kwargs)
        if isinstance(asli, IndeksBruteForce):
            return asli
        # Kalau pembungkusnya gagal (mis. RAM tidak cukup untuk menyalin
        # vektornya), JANGAN kembalikan index faiss mentah: index.search()-nya
        # justru yang segfault dan akan merobohkan seluruh layanan. Dengan
        # melempar, pipeline rvc-python menangkap sendiri dan mematikan index
        # (index = big_npy = None) -- suara tetap keluar, cuma kurang mirip.
        disambung = IndeksBruteForce(asli)
        log(
            f"[index] brute-force numpy aktif: {disambung.ntotal} vektor "
            f"x {disambung.d} dim, metrik "
            f"{'IP' if disambung.metric_type == METRIK_IP else 'L2'}"
        )
        return disambung

    baca_berbungkus._huohuo_tampalan = True
    faiss.read_index = baca_berbungkus
    return True


if __name__ == "__main__":
    import sys
    from pathlib import Path

    jalur = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).resolve().parents[1] / "assets/rvc/HuoHuo"
        / "added_IVF273_Flat_nprobe_1_HuoHuo_v2.index"
    )
    import faiss

    pasang()
    idx = faiss.read_index(jalur)
    rng = np.random.default_rng(0)
    D, I = idx.search(rng.random((64, idx.d), dtype="float32"), k=8)
    print("search OK", D.shape, I.shape)
    print("baris 0 skor:", np.round(D[0], 3), "indeks:", I[0])
