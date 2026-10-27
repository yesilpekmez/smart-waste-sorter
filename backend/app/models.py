from __future__ import annotations

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

WASTE_CLASSES = ("plastic", "paper", "glass", "metal")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    # SQLite saat dilimini saklamaz; tüm zamanlar UTC
    return dt.replace(tzinfo=timezone.utc).isoformat()


class Bin(db.Model):
    type = db.Column(db.String(16), primary_key=True)
    fill = db.Column(db.Integer, nullable=False, default=0)  # yüzde
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {"type": self.type, "fill": self.fill, "updatedAt": _iso(self.updated_at)}


class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(16), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    # Kutu, karenin yüzdesi olarak
    box_x = db.Column(db.Float, nullable=False)
    box_y = db.Column(db.Float, nullable=False)
    box_w = db.Column(db.Float, nullable=False)
    box_h = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "box": {"x": self.box_x, "y": self.box_y, "w": self.box_w, "h": self.box_h},
            "imageUrl": f"/api/detections/{self.id}/image" if self.image_path else None,
            "createdAt": _iso(self.created_at),
        }


class Operation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    detection_id = db.Column(db.Integer, db.ForeignKey("detection.id"), nullable=False)
    target_bin = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(16), nullable=False)  # completed | rejected
    reason = db.Column(db.String(32))  # uncertain | bin_full
    created_at = db.Column(db.DateTime, nullable=False, default=_now)

    detection = db.relationship("Detection")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "detectionId": self.detection_id,
            "label": self.detection.label,
            "confidence": round(self.detection.confidence, 4),
            "targetBin": self.target_bin,
            "status": self.status,
            "reason": self.reason,
            "createdAt": _iso(self.created_at),
        }
