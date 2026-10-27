"""TrashNet veri setini indirip projenin dört sınıfına göre hazırlar.

Çıktı (YOLO sınıflandırma biçimi):
    datasets/trashnet/{train,val,test}/{glass,metal,paper,plastic}/*.jpg

Karton fotoğrafları kâğıt sınıfına katılır, "trash" sınıfı kullanılmaz.

Kullanım:
    .venv/bin/python prepare_trashnet.py
"""
from __future__ import annotations

import random
import shutil
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

URL = "https://huggingface.co/datasets/garythung/trashnet/resolve/main/dataset-resized.zip"
ROOT = Path(__file__).resolve().parent / "datasets"
ZIP_PATH = ROOT / "raw" / "trashnet-resized.zip"
OUT_DIR = ROOT / "trashnet"

CLASS_MAP = {
    "glass": "glass",
    "metal": "metal",
    "paper": "paper",
    "cardboard": "paper",
    "plastic": "plastic",
}
SPLITS = {"train": 0.70, "val": 0.15, "test": 0.15}
SEED = 42


def download() -> None:
    if ZIP_PATH.exists():
        return
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"İndiriliyor: {URL}")
    urllib.request.urlretrieve(URL, ZIP_PATH)


def collect() -> dict[str, list[tuple[str, bytes]]]:
    """Zip içindeki görüntüleri hedef sınıflara göre gruplar."""
    images: dict[str, list[tuple[str, bytes]]] = {c: [] for c in set(CLASS_MAP.values())}
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for name in sorted(zf.namelist()):
            parts = Path(name).parts
            if not name.lower().endswith(".jpg") or "__MACOSX" in parts or len(parts) < 2:
                continue
            source_class = parts[-2]
            if source_class in CLASS_MAP:
                images[CLASS_MAP[source_class]].append((Path(name).name, zf.read(name)))
    return images


def main() -> None:
    download()
    images = collect()

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    rng = random.Random(SEED)
    counts: Counter = Counter()
    # Her sınıf ayrı bölündüğü için sınıf oranları üç kümede de korunur
    for cls, items in images.items():
        rng.shuffle(items)
        n_train = int(len(items) * SPLITS["train"])
        n_val = int(len(items) * SPLITS["val"])
        bounds = {"train": items[:n_train], "val": items[n_train : n_train + n_val], "test": items[n_train + n_val :]}
        for split, split_items in bounds.items():
            target = OUT_DIR / split / cls
            target.mkdir(parents=True, exist_ok=True)
            for filename, data in split_items:
                (target / filename).write_bytes(data)
            counts[(split, cls)] = len(split_items)

    classes = sorted(images)
    print(f"\n{'':8}" + "".join(f"{c:>9}" for c in classes) + f"{'toplam':>9}")
    for split in SPLITS:
        row = [counts[(split, c)] for c in classes]
        print(f"{split:8}" + "".join(f"{n:>9}" for n in row) + f"{sum(row):>9}")
    print(f"\nHazır: {OUT_DIR}")


if __name__ == "__main__":
    main()
