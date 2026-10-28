from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

WASTE_CLASSES = ("plastic", "paper", "glass", "metal")

# running: hareket sürüyor
# completed: atık bölmeye bırakıldı
# rejected: yazılım kuralı ayırmayı engelledi (uncertain, bin_full)
# aborted: başlatılamadı ama arıza değil (no_item)
# failed: donanım arızası (jam, timeout, driver_error, interrupted…)
OPERATION_STATUSES = ("running", "completed", "rejected", "aborted", "failed")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    # SQLite saat dilimini saklamaz; tüm zamanlar UTC
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


class Bin(db.Model):
    type = db.Column(db.String(16), primary_key=True)
    fill = db.Column(db.Integer, nullable=False, default=0)  # yaklaşık yüzde (yığın yüksekliği)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {"type": self.type, "fill": self.fill, "updatedAt": _iso(self.updated_at)}


class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(16), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    model_version = db.Column(db.String(64), nullable=False)
    # Kutu, karenin yüzdesi olarak; sınıflandırma modelinde kutu yoktur
    box_x = db.Column(db.Float)
    box_y = db.Column(db.Float)
    box_w = db.Column(db.Float)
    box_h = db.Column(db.Float)
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    operation = db.relationship("Operation", back_populates="detection", uselist=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "modelVersion": self.model_version,
            "box": None
            if self.box_x is None
            else {"x": self.box_x, "y": self.box_y, "w": self.box_w, "h": self.box_h},
            "imageUrl": f"/api/detections/{self.id}/image" if self.image_path else None,
            "createdAt": _iso(self.created_at),
        }


class Operation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Her algılama en fazla bir kez işlenebilir; eşzamanlı istekleri veritabanı da engeller
    detection_id = db.Column(db.Integer, db.ForeignKey("detection.id"), nullable=False, unique=True)
    target_bin = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(16), nullable=False)
    reason = db.Column(db.String(32))
    message = db.Column(db.String(255))
    # Kararın verildiği andaki eşikler
    min_confidence = db.Column(db.Float, nullable=False)
    full_threshold = db.Column(db.Integer, nullable=False)
    # Kontrol servisinin aşama süreleri: [[durum, saniye], ...]
    trace = db.Column(db.Text)
    duration_ms = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    finished_at = db.Column(db.DateTime)

    detection = db.relationship("Detection", back_populates="operation")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "detectionId": self.detection_id,
            "label": self.detection.label,
            "confidence": round(self.detection.confidence, 4),
            "modelVersion": self.detection.model_version,
            "targetBin": self.target_bin,
            "imageUrl": self.detection.to_dict()["imageUrl"],
            "status": self.status,
            "reason": self.reason,
            "message": self.message,
            "minConfidence": self.min_confidence,
            "fullThreshold": self.full_threshold,
            "trace": json.loads(self.trace) if self.trace else [],
            "durationMs": self.duration_ms,
            "createdAt": _iso(self.created_at),
            "finishedAt": _iso(self.finished_at),
        }
