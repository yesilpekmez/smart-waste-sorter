"""YOLOv8 sınıflandırma modelini aktarım öğrenmesiyle eğitir.

ImageNet üzerinde önceden eğitilmiş yolov8n-cls ağırlıklarından başlar.
En iyi model weights/best.pt olarak kopyalanır; backend bu dosyayı kullanır.

Kullanım:
    .venv/bin/python train.py                     # TrashNet, 30 epoch
    .venv/bin/python train.py --data datasets/kendi --epochs 50
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import torch
from ultralytics import YOLO

AI_DIR = Path(__file__).resolve().parent


def pick_device() -> str:
    if torch.cuda.is_available():
        return "0"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(AI_DIR / "datasets" / "trashnet"))
    parser.add_argument("--model", default="yolov8n-cls.pt")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--name", default="trashnet")
    parser.add_argument("--device", default=pick_device())
    args = parser.parse_args()

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(AI_DIR / "runs"),
        name=args.name,
        exist_ok=True,
        patience=10,  # doğrulama başarısı 10 epoch iyileşmezse durur
        seed=42,
    )

    best = Path(model.trainer.best)
    target = AI_DIR / "weights" / "best.pt"
    target.parent.mkdir(exist_ok=True)
    shutil.copy(best, target)
    print(f"\nEn iyi model: {target}")


if __name__ == "__main__":
    main()
