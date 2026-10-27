"""Eğitilmiş modeli test kümesinde değerlendirir.

Doğruluk, sınıf bazında kesinlik/duyarlılık/F1, makro F1 ve karışıklık
matrisini yazdırır; sonuçları reports/ altına JSON olarak kaydeder.

Kullanım:
    .venv/bin/python evaluate.py
    .venv/bin/python evaluate.py --weights weights/best.pt --data datasets/kendi/test
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from ultralytics import YOLO

AI_DIR = Path(__file__).resolve().parent
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default=str(AI_DIR / "weights" / "best.pt"))
    parser.add_argument("--data", default=str(AI_DIR / "datasets" / "trashnet" / "test"))
    parser.add_argument("--min-confidence", type=float, default=0.6, help="backend'deki eşikle aynı")
    args = parser.parse_args()

    model = YOLO(args.weights)
    classes = sorted(p.name for p in Path(args.data).iterdir() if p.is_dir())
    matrix = {t: {p: 0 for p in classes} for t in classes}
    low_confidence = 0
    low_confidence_correct = 0
    total = 0

    for true_cls in classes:
        files = [f for f in sorted((Path(args.data) / true_cls).iterdir()) if f.suffix.lower() in IMAGE_EXTS]
        for result in model.predict([str(f) for f in files], verbose=False, stream=True):
            pred_cls = result.names[result.probs.top1]
            matrix[true_cls][pred_cls] += 1
            total += 1
            if float(result.probs.top1conf) < args.min_confidence:
                low_confidence += 1
                low_confidence_correct += pred_cls == true_cls

    per_class = {}
    for c in classes:
        tp = matrix[c][c]
        fp = sum(matrix[t][c] for t in classes if t != c)
        fn = sum(matrix[c][p] for p in classes if p != c)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[c] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}

    accuracy = sum(matrix[c][c] for c in classes) / total
    macro_f1 = sum(m["f1"] for m in per_class.values()) / len(classes)

    print(f"\nTest görüntüsü: {total}")
    print(f"Doğruluk:       {accuracy:.3f}")
    print(f"Makro F1:       {macro_f1:.3f}")
    print(
        f"Güven < {args.min_confidence}: {low_confidence} görüntü "
        f"(bunların {low_confidence_correct} tanesi doğruydu; sistem bunları ayırmaz)\n"
    )
    print(f"{'sınıf':10}{'kesinlik':>10}{'duyarlılık':>12}{'F1':>8}{'adet':>7}")
    for c, m in per_class.items():
        print(f"{c:10}{m['precision']:>10.3f}{m['recall']:>12.3f}{m['f1']:>8.3f}{m['support']:>7}")

    print("\nKarışıklık matrisi (satır: gerçek, sütun: tahmin)")
    print(f"{'':10}" + "".join(f"{c:>9}" for c in classes))
    for t in classes:
        print(f"{t:10}" + "".join(f"{matrix[t][p]:>9}" for p in classes))

    report_dir = AI_DIR / "reports"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"eval-{datetime.now():%Y%m%d-%H%M%S}.json"
    report_path.write_text(
        json.dumps(
            {
                "weights": args.weights,
                "data": args.data,
                "total": total,
                "accuracy": accuracy,
                "macro_f1": macro_f1,
                "low_confidence": low_confidence,
                "per_class": per_class,
                "confusion_matrix": matrix,
            },
            indent=2,
        )
    )
    print(f"\nRapor: {report_path}")


if __name__ == "__main__":
    main()
