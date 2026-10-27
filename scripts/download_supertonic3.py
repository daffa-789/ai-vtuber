"""Download the pinned Supertonic 3 model assets for offline use."""

from __future__ import annotations

from pathlib import Path

from huggingface_hub import snapshot_download


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "assets" / "supertonic-3"
REPO_ID = "supertone-oss-archive/supertonic-3"
REVISION = "aafc6e32416a594460b32413efc49d7fe4ce6d46"


def main() -> None:
    print(f"Mengunduh {REPO_ID} ke {MODEL_DIR}")
    snapshot_download(
        repo_id=REPO_ID,
        revision=REVISION,
        local_dir=str(MODEL_DIR),
    )
    if not any(MODEL_DIR.rglob("*.onnx")):
        raise SystemExit("Unduhan selesai tetapi berkas ONNX tidak ditemukan.")
    print("Selesai. Sintesis berikutnya berjalan lokal tanpa mengunduh model lagi.")


if __name__ == "__main__":
    main()
