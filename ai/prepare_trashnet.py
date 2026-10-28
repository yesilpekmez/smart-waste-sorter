"""TrashNet veri setini indirip projenin dört sınıfına göre hazırlar.

Çıktı (YOLO sınıflandırma biçimi):
    datasets/trashnet/{train,val,test}/{glass,metal,paper,plastic}/*.jpg

Karton fotoğrafları kâğıt sınıfına katılır, "trash" sınıfı kullanılmaz.

Bölünme splits/trashnet-v1.csv dosyasında saklanır ve git'e eklenir. Dosya
varsa bölünme oradan okunur; böylece her çalıştırmada aynı test kümesi oluşur
ve farklı modeller aynı görüntüler üzerinde karşılaştırılabilir.

Kullanım:
    .venv/bin/python prepare_trashnet.py                # kayıtlı bölünmeyi kullan
    .venv/bin/python prepare_trashnet.py --save-current # diskteki bölünmeyi kaydet
"""
from __future__ import annotations

import argparse
import csv
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
MANIFEST = Path(__file__).resolve().parent / "splits" / "trashnet-v1.csv"

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
    # Sınıflar sıralı dolaşılır; set sırası süreçten sürece değişebilir
    images: dict[str, list[tuple[str, bytes]]] = {c: [] for c in sorted(set(CLASS_MAP.values()))}
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for name in sorted(zf.namelist()):
            parts = Path(name).parts
            if not name.lower().endswith(".jpg") or "__MACOSX" in parts or len(parts) < 2:
                continue
            source_class = parts[-2]
            if source_class in CLASS_MAP:
                images[CLASS_MAP[source_class]].append((Path(name).name, zf.read(name)))
    return images


def random_split(images: dict) -> list[tuple[str, str, str]]:
    """(küme, sınıf, dosya) satırları. Her sınıf ayrı bölündüğü için oranlar korunur."""
    rng = random.Random(SEED)
    rows = []
    for cls in sorted(images):
        names = sorted(name for name, _ in images[cls])
        rng.shuffle(names)
        n_train = int(len(names) * SPLITS["train"])
        n_val = int(len(names) * SPLITS["val"])
        for i, name in enumerate(names):
            split = "train" if i < n_train else "val" if i < n_train + n_val else "test"
            rows.append((split, cls, name))
    return rows


def read_manifest() -> list[tuple[str, str, str]]:
    with MANIFEST.open() as f:
        return [(r["split"], r["class"], r["file"]) for r in csv.DictReader(f)]


def write_manifest(rows: list[tuple[str, str, str]]) -> None:
    MANIFEST.parent.mkdir(exist_ok=True)
    with MANIFEST.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "class", "file"])
        writer.writerows(sorted(rows))
    print(f"Bölünme kaydedildi: {MANIFEST}")


def save_current() -> None:
    """Diskteki mevcut bölünmeyi dosya listesine dönüştürür."""
    rows = [
        (split_dir.name, cls_dir.name, f.name)
        for split_dir in sorted(OUT_DIR.iterdir())
        if split_dir.is_dir()
        for cls_dir in sorted(split_dir.iterdir())
        if cls_dir.is_dir()
        for f in sorted(cls_dir.glob("*.jpg"))
    ]
    write_manifest(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-current", action="store_true", help="diskteki bölünmeyi kaydet ve çık")
    args = parser.parse_args()
    if args.save_current:
        save_current()
        return

    download()
    images = collect()

    if MANIFEST.exists():
        rows = read_manifest()
        print(f"Kayıtlı bölünme kullanılıyor: {MANIFEST.name}")
    else:
        rows = random_split(images)
        write_manifest(rows)

    data = {(cls, name): blob for cls, items in images.items() for name, blob in items}
    missing = [(c, n) for _, c, n in rows if (c, n) not in data]
    if missing:
        raise SystemExit(f"Bölünmedeki {len(missing)} dosya zip'te yok, ör. {missing[0]}")

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    counts: Counter = Counter()
    for split, cls, name in rows:
        target = OUT_DIR / split / cls
        target.mkdir(parents=True, exist_ok=True)
        (target / name).write_bytes(data[(cls, name)])
        counts[(split, cls)] += 1

    classes = sorted(images)
    print(f"\n{'':8}" + "".join(f"{c:>9}" for c in classes) + f"{'toplam':>9}")
    for split in SPLITS:
        row = [counts[(split, c)] for c in classes]
        print(f"{split:8}" + "".join(f"{n:>9}" for n in row) + f"{sum(row):>9}")
    print(f"\nHazır: {OUT_DIR}")


if __name__ == "__main__":
    main()
