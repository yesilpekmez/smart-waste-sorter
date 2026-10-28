from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, jsonify, request, send_file
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func

from controller import ControllerFault

from . import sorting
from .control import controller, simulator, sync_bins
from .models import OPERATION_STATUSES, WASTE_CLASSES, Bin, Detection, Operation, db

api = Blueprint("api", __name__, url_prefix="/api")


def error(message: str, status: int, code: str | None = None):
    body = {"error": message}
    if code:
        body["code"] = code
    return jsonify(body), status


def exclusive_command(fn):
    """Analiz, ayırma ve sıfırlama aynı atık döngüsünü paylaşır."""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        lock = current_app.extensions["command_lock"]
        if not lock.acquire(blocking=False):
            return error("Başka bir işlem sürüyor", 409, "busy")
        try:
            return fn(*args, **kwargs)
        finally:
            lock.release()
    return wrapped


@api.errorhandler(ControllerFault)
def hardware_error(fault):
    return error(fault.message, 503, fault.code)


def classifier():
    return current_app.extensions["classifier"]


def detection_payload(detection: Detection) -> dict:
    """Algılamayı, işlem durumu ve şu an ayrılıp ayrılamayacağıyla birlikte döndürür."""
    sync_bins()
    refused = sorting.refusal(detection)
    blocked = None
    if detection.operation is None:
        blocked = sorting.rejection_reason(detection, db.session.get(Bin, detection.label))
    return {
        **detection.to_dict(),
        "operation": detection.operation.to_dict() if detection.operation else None,
        "sortable": refused is None,
        "refusal": None if refused is None else {"code": refused.code, "message": refused.message},
        "blockedReason": blocked,
    }


@api.get("/health")
def health():
    return {
        "status": "ok",
        "classifier": classifier().name,
        "modelVersion": classifier().version,
        "hardware": current_app.config["HARDWARE"],
        "minConfidence": current_app.config["MIN_CONFIDENCE"],
        "fullThreshold": current_app.config["FULL_THRESHOLD"],
    }


@api.get("/system")
def system_status():
    running = sorting.running_operation()
    return {
        **controller().status(),
        "itemPresent": controller().item_present(),
        "runningOperationId": running.id if running else None,
    }


@api.post("/system/reset")
@exclusive_command
def system_reset():
    try:
        controller().reset()
    except ControllerFault as fault:
        return error(fault.message, 503, fault.code)
    return system_status()


@api.get("/bins")
def list_bins():
    bins = {b.type: b for b in sync_bins()}
    return jsonify([bins[t].to_dict() for t in WASTE_CLASSES])


@api.post("/bins/<bin_type>/empty")
@exclusive_command
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
@exclusive_command
def detect():
    """Kameradan alınan kareyi ya da yüklenen fotoğrafı sınıflandırır.

    Görüntü gönderilmezse yalnızca örnek sınıflandırıcı sonuç üretebilir.
    """
    running = sorting.running_operation()
    if running is not None:
        return error("Ayırma sürüyor; bitmeden yeni atık algılanamaz", 409, "busy")

    image = None
    upload = request.files.get("image")
    if upload:
        try:
            image = Image.open(upload.stream).convert("RGB")
        except (UnidentifiedImageError, OSError):
            return error("Geçersiz görüntü dosyası", 400, "invalid_image")
    elif classifier().needs_image:
        return error("Sınıflandırma için görüntü gerekli", 400, "image_required")

    prediction = classifier().predict(image)
    if prediction is None:
        return error("Görüntüde atık algılanamadı", 422, "no_detection")

    x, y, w, h = prediction.box or (None, None, None, None)
    detection = Detection(
        label=prediction.label,
        confidence=prediction.confidence,
        model_version=classifier().version,
        box_x=x,
        box_y=y,
        box_w=w,
        box_h=h,
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
    detection = sorting.latest_detection()
    if detection is None:
        return error("Henüz algılama yok", 404, "no_detection")
    return detection_payload(detection)


@api.get("/detections/<int:detection_id>/image")
def detection_image(detection_id: int):
    detection = db.session.get(Detection, detection_id)
    if detection is None or not detection.image_path:
        return error("Görüntü bulunamadı", 404)
    return send_file(detection.image_path, mimetype="image/jpeg")


@api.post("/sort")
@exclusive_command
def sort():
    body = request.get_json(silent=True)
    detection_id = body.get("detectionId") if isinstance(body, dict) else None
    # bool da int'in alt türü; true/false kimlik olarak kabul edilmez
    if not isinstance(detection_id, int) or isinstance(detection_id, bool):
        return error("detectionId tam sayı olmalı", 400, "invalid_request")

    detection = db.session.get(Detection, detection_id)
    if detection is None:
        return error("Algılama bulunamadı", 404)

    try:
        op = sorting.sort(detection)
    except sorting.SortRefused as refused:
        return error(refused.message, 409, refused.code)
    return {"operation": op.to_dict(), "bin": db.session.get(Bin, detection.label).to_dict()}, 201


@api.get("/operations")
def list_operations():
    limit = min(max(request.args.get("limit", 20, type=int), 1), 100)
    offset = max(request.args.get("offset", 0, type=int), 0)
    label = request.args.get("label")
    status = request.args.get("status")
    if label and label not in WASTE_CLASSES:
        return error("Bilinmeyen atık türü", 400, "invalid_request")
    if status and status not in OPERATION_STATUSES:
        return error("Bilinmeyen işlem durumu", 400, "invalid_request")

    query = Operation.query.join(Detection)
    if label:
        query = query.filter(Detection.label == label)
    if status:
        query = query.filter(Operation.status == status)

    total = query.count()
    ops = query.order_by(Operation.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [op.to_dict() for op in ops]}


@api.get("/stats")
def stats():
    finished = [s for s in OPERATION_STATUSES if s != "running"]
    rows = (
        db.session.query(Detection.label, Operation.status, func.count(Operation.id))
        .join(Detection)
        .filter(Operation.status != "running")
        .group_by(Detection.label, Operation.status)
        .all()
    )
    by_class = {c: {s: 0 for s in finished} for c in WASTE_CLASSES}
    for label, status, count in rows:
        by_class[label][status] = count

    totals = {s: sum(c[s] for c in by_class.values()) for s in finished}
    total = sum(totals.values())
    avg_conf = (
        db.session.query(func.avg(Detection.confidence)).join(Operation).filter(Operation.status != "running").scalar()
    )
    avg_duration = db.session.query(func.avg(Operation.duration_ms)).filter_by(status="completed").scalar()
    return {
        "total": total,
        **totals,
        "successRate": totals["completed"] / total if total else None,
        "averageConfidence": avg_conf,
        "averageDurationMs": avg_duration,
        "byClass": by_class,
    }


SIM_FAULTS = {"jam", "position", "home", "stall", "gate_error", "stop_error"}


@api.route("/sim/faults", methods=["GET", "PUT"])
@exclusive_command
def sim_faults():
    """Simülasyonda arıza denemek için (yalnızca simülasyon modunda)."""
    sim = simulator()
    if sim is None:
        return error("Yalnızca simülasyon modunda kullanılabilir", 404)
    if request.method == "PUT":
        body = request.get_json(silent=True)
        faults = body.get("faults") if isinstance(body, dict) else None
        if not isinstance(faults, list) or any(not isinstance(f, str) or f not in SIM_FAULTS for f in faults):
            return error(f"faults şunlardan oluşan bir liste olmalı: {sorted(SIM_FAULTS)}", 400, "invalid_request")
        sim.world.faults = set(faults)
    return {"faults": sorted(sim.world.faults)}
