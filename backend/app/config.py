import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'ayir.db'}")
    UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

    # Eğitilmiş YOLO ağırlıkları; dosya yoksa örnek sınıflandırıcı kullanılır
    MODEL_PATH = os.environ.get("MODEL_PATH", str(BASE_DIR.parent / "ai" / "weights" / "best.pt"))

    # Bu güvenin altındaki tahminlerde ayırma durdurulur
    MIN_CONFIDENCE = 0.6
    # Bu oranın üzerindeki bölmelere atık gönderilmez
    FULL_THRESHOLD = 90
