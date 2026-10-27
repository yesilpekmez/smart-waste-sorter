from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_file
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func

from controller import ControllerFault

from . import sorting
from .control import controller, simulator, sync_bins
from .models import WASTE_CLASSES, Bin, Detection, Operation, db

api = Blueprint("api", __name__, url_prefix="/api")


def error(message: str, status: int):
    return jsonify({"error": message}), status


def detection_payload(detection: Detection) -> dict:
    sync_bins()
    bin_ = db.session.get(Bin, detection.label)
    return {**detection.to_dict(), "blockedReason": sorting.rejection_reason(detection, bin_)}


@api.get("/health")
def health():
    return {
        "status": "ok",
        "classifier": current_app.extensions["classifier"].name,
        "hardware": current_app.config["HARDWARE"],
    }


@api.get("/system")
def system_status():
    return {**controller().status(), "itemPresent": controller().item_present()}


@api.post("/system/reset")
def system_reset():
    try:
        controller().reset()
    except ControllerFault as fault:
        return error(fault.message, 503)
    return system_status()


@api.get("/bins")
def list_bins():
    bins = {b.type: b for b in sync_bins()}
    return jsonify([bins[t].to_dict() for t in WASTE_CLASSES])


@api.post("/bins/<bin_type>/empty")
def empty_bin(bin_type: str):
    if bin_type not in WASTE_CLASSES:
        return error("Bölme bulunamadı", 404)
    sim = simulator()
    if sim is None:
        # Gerçek sistemde bölme elle boşaltılır; sensörler yeni seviyeyi okur
        return error("Bölmeyi fiziksel olarak boşaltın", 400)
    sim.empty_bin(bin_type)
    sync_bins()
    return db.session.get(Bin, bin_type).to_dict()


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

    x, y, w, h = prediction.box or (None, None, None, None)
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
    if simulator():
        simulator().place_item()  # kamera platformda yeni bir atık gördü
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

    try:
        op = sorting.sort(detection)
    except ControllerFault as fault:
        return jsonify({"error": fault.message, "code": fault.code}), 409
    return {"operation": op.to_dict(), "bin": db.session.get(Bin, detection.label).to_dict()}, 201


@api.get("/operations")
def list_operations():
    limit = min(request.args.get("limit", 20, type=int), 100)
    offset = max(request.args.get("offset", 0, type=int), 0)
    query = Operation.query.join(Detection)
    if request.args.get("label"):
        query = query.filter(Detection.label == request.args["label"])
    if request.args.get("status"):
        query = query.filter(Operation.status == request.args["status"])

    total = query.count()
    ops = query.order_by(Operation.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [op.to_dict() for op in ops]}


@api.get("/stats")
def stats():
    rows = (
        db.session.query(Detection.label, Operation.status, func.count(Operation.id))
        .join(Detection)
        .group_by(Detection.label, Operation.status)
        .all()
    )
    by_class = {c: {"completed": 0, "rejected": 0, "failed": 0} for c in WASTE_CLASSES}
    for label, status, count in rows:
        by_class[label][status] = count

    totals = {s: sum(c[s] for c in by_class.values()) for s in ("completed", "rejected", "failed")}
    total = sum(totals.values())
    avg_conf = db.session.query(func.avg(Detection.confidence)).join(Operation).scalar()
    return {
        "total": total,
        **totals,
        "successRate": totals["completed"] / total if total else None,
        "averageConfidence": avg_conf,
        "byClass": by_class,
    }
