from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_file
from PIL import Image, UnidentifiedImageError

from . import sorting
from .models import WASTE_CLASSES, Bin, Detection, Operation, db

api = Blueprint("api", __name__, url_prefix="/api")


def error(message: str, status: int):
    return jsonify({"error": message}), status


def detection_payload(detection: Detection) -> dict:
    bin_ = db.session.get(Bin, detection.label)
    return {**detection.to_dict(), "blockedReason": sorting.rejection_reason(detection, bin_)}


@api.get("/health")
def health():
    return {"status": "ok", "classifier": current_app.extensions["classifier"].name}


@api.get("/bins")
def list_bins():
    bins = {b.type: b for b in Bin.query.all()}
    return jsonify([bins[t].to_dict() for t in WASTE_CLASSES])


@api.post("/bins/<bin_type>/empty")
def empty_bin(bin_type: str):
    bin_ = db.session.get(Bin, bin_type)
    if bin_ is None:
        return error("Bölme bulunamadı", 404)
    bin_.fill = 0
    db.session.commit()
    return bin_.to_dict()


@api.post("/detect")
def detect():
    """Fotoğraf yüklenirse onu sınıflandırır; yoksa kameradan kare alınmış gibi davranır."""
    image = None
    upload = request.files.get("image")
    if upload:
        try:
            image = Image.open(upload.stream).convert("RGB")
        except UnidentifiedImageError:
            return error("Geçersiz görüntü dosyası", 400)

    prediction = current_app.extensions["classifier"].predict(image)
    if prediction is None:
        return error("Görüntüde atık algılanamadı", 422)

    x, y, w, h = prediction.box
    detection = Detection(
        label=prediction.label, confidence=prediction.confidence, box_x=x, box_y=y, box_w=w, box_h=h
    )
    db.session.add(detection)
    db.session.flush()

    if image is not None:
        upload_dir = current_app.config["UPLOAD_DIR"]
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / f"{detection.id}.jpg"
        image.save(path, "JPEG", quality=90)
        detection.image_path = str(path)

    db.session.commit()
    return detection_payload(detection), 201


@api.get("/detections/latest")
def latest_detection():
    detection = Detection.query.order_by(Detection.id.desc()).first()
    if detection is None:
        return error("Henüz algılama yok", 404)
    return detection_payload(detection)


@api.get("/detections/<int:detection_id>/image")
def detection_image(detection_id: int):
    detection = db.session.get(Detection, detection_id)
    if detection is None or not detection.image_path:
        return error("Görüntü bulunamadı", 404)
    return send_file(detection.image_path, mimetype="image/jpeg")


@api.post("/sort")
def sort():
    body = request.get_json(silent=True) or {}
    detection = db.session.get(Detection, body.get("detectionId"))
    if detection is None:
        return error("Algılama bulunamadı", 404)
    if Operation.query.filter_by(detection_id=detection.id).first():
        return error("Bu atık zaten işlendi", 409)

    op = sorting.sort(detection)
    return {"operation": op.to_dict(), "bin": db.session.get(Bin, detection.label).to_dict()}, 201


@api.get("/operations")
def list_operations():
    limit = min(request.args.get("limit", 20, type=int), 100)
    ops = Operation.query.order_by(Operation.id.desc()).limit(limit).all()
    return jsonify([op.to_dict() for op in ops])
