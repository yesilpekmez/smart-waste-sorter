"""Atık sınıflandırıcıları.

Eğitilmiş YOLO ağırlıkları varsa onu, yoksa rastgele sonuç üreten örnek
sınıflandırıcıyı kullanır. İkisi de aynı biçimde sonuç döndürür.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image

from .models import WASTE_CLASSES


@dataclass
class Prediction:
    label: str
    confidence: float
    box: tuple  # (x, y, w, h), karenin yüzdesi olarak


class MockClassifier:
    name = "mock"

    def predict(self, image: Optional[Image.Image]) -> Prediction:
        label = random.choice(WASTE_CLASSES)
        # Arada bir belirsiz tahmin üretir
        if random.random() < 0.15:
            confidence = random.uniform(0.4, 0.58)
        else:
            confidence = random.uniform(0.8, 0.99)
        w, h = random.uniform(18, 32), random.uniform(45, 75)
        return Prediction(label, confidence, (50 - w / 2, 50 - h / 2, w, h))


class YoloClassifier:
    name = "yolo"

    def __init__(self, model_path: str):
        from ultralytics import YOLO

        self.model = YOLO(model_path)

    def predict(self, image: Optional[Image.Image]) -> Optional[Prediction]:
        if image is None:
            return None
        result = self.model.predict(image, verbose=False)[0]
        if len(result.boxes) == 0:
            return None
        best = max(result.boxes, key=lambda b: float(b.conf))
        label = result.names[int(best.cls)]
        if label not in WASTE_CLASSES:
            return None
        x1, y1, x2, y2 = best.xyxy[0].tolist()
        iw, ih = image.size
        box = (x1 / iw * 100, y1 / ih * 100, (x2 - x1) / iw * 100, (y2 - y1) / ih * 100)
        return Prediction(label, float(best.conf), box)


def load_classifier(model_path: str):
    if Path(model_path).is_file():
        try:
            return YoloClassifier(model_path)
        except ImportError:
            pass
    return MockClassifier()
