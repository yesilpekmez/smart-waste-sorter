"""Atık döngüsü, eşzamanlılık ve arıza senaryoları."""
import threading

import pytest

from app import create_app
from app.classifier import Prediction
from app.models import Detection, Operation, db


def detect(client):
    return client.post("/api/detect").get_json()


def sort(client, detection_id):
    return client.post("/api/sort", json={"detectionId": detection_id})


def test_stale_detection_cannot_be_sorted(client, classifier, world):
    classifier.next = Prediction("plastic", 0.95)
    old = detect(client)
    classifier.next = Prediction("glass", 0.95)
    new = detect(client)

    res = sort(client, old["id"])
    assert res.status_code == 409
    assert res.get_json()["code"] == "stale"
    assert world.levels["plastic"] == pytest.approx(42 * 25 / 100)  # plastik bölmeye bir şey düşmedi

    assert sort(client, new["id"]).status_code == 201
    assert world.levels["glass"] > 65 * 25 / 100


def test_detect_refused_while_sorting(app, client):
    d = detect(client)
    with app.app_context():
        db.session.add(Operation(detection_id=d["id"], target_bin="plastic", status="running", min_confidence=0.6, full_threshold=90))
        db.session.commit()

    res = client.post("/api/detect")
    assert res.status_code == 409
    assert res.get_json()["code"] == "busy"


def test_concurrent_sorts_run_only_once(tmp_path, monkeypatch):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'c.db'}",
            "UPLOAD_DIR": tmp_path / "uploads",
            "SIM_TIME_SCALE": 0.05,  # hareket kısa da olsa sürsün
            "MODEL_PATH": str(tmp_path / "yok.pt"),
        }
    )
    d = app.test_client().post("/api/detect").get_json()

    codes = []
    barrier = threading.Barrier(2)

    def worker():
        client = app.test_client()
        barrier.wait()
        codes.append(client.post("/api/sort", json={"detectionId": d["id"]}).status_code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(codes) == [201, 409]
    with app.app_context():
        assert Operation.query.count() == 1


def test_latest_detection_reports_processed_state(client):
    d = detect(client)
    assert detect_latest(client)["sortable"] is True
    sort(client, d["id"])

    latest = detect_latest(client)
    assert latest["sortable"] is False
    assert latest["refusal"]["code"] == "processed"
    assert latest["operation"]["status"] == "completed"
    assert latest["blockedReason"] is None


def detect_latest(client):
    return client.get("/api/detections/latest").get_json()


def test_no_item_is_aborted_not_fault(client, world):
    d = detect(client)
    world.item_on_platform = False  # atık kamera karesinden sonra alındı

    op = sort(client, d["id"]).get_json()["operation"]
    assert (op["status"], op["reason"]) == ("aborted", "no_item")
    assert client.get("/api/system").get_json()["state"] == "idle"


def test_driver_error_is_recorded_as_fault(client, world):
    world.faults.add("gate_error")
    d = detect(client)
    op = sort(client, d["id"]).get_json()["operation"]

    assert (op["status"], op["reason"]) == ("failed", "driver_error")
    assert "OSError" in op["message"]
    system = client.get("/api/system").get_json()
    assert system["state"] == "fault"
    assert system["fault"]["code"] == "driver_error"


def test_failed_reset_keeps_fault(client, world):
    world.faults.add("jam")
    sort(client, detect(client)["id"])

    world.faults = {"home"}
    res = client.post("/api/system/reset")
    assert res.status_code == 503
    assert res.get_json()["code"] == "home_error"
    assert client.get("/api/system").get_json()["state"] == "fault"


def test_operation_records_thresholds_trace_and_model(client):
    op = sort(client, detect(client)["id"]).get_json()["operation"]
    assert op["minConfidence"] == 0.6
    assert op["fullThreshold"] == 90
    assert op["modelVersion"] == "fixed-test"
    assert [s for s, _ in op["trace"]] == ["routing", "dropping", "verifying", "returning", "idle"]
    assert op["durationMs"] is not None
    assert op["finishedAt"] is not None


@pytest.mark.parametrize(
    "body",
    [None, [], {"detectionId": "1"}, {"detectionId": True}, {"detectionId": [1]}, {"detectionId": None}, {}],
)
def test_sort_validates_request(client, body):
    detect(client)
    kwargs = {} if body is None else {"json": body}
    res = client.post("/api/sort", **kwargs)
    assert res.status_code == 400
    assert res.get_json()["code"] == "invalid_request"


def test_operations_validates_filters(client):
    assert client.get("/api/operations?status=bilinmez").status_code == 400
    assert client.get("/api/operations?label=tahta").status_code == 400


def test_interrupted_operation_recovered_on_startup(tmp_path):
    config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'r.db'}",
        "UPLOAD_DIR": tmp_path / "uploads",
        "SIM_TIME_SCALE": 0,
        "MODEL_PATH": str(tmp_path / "yok.pt"),
    }
    app = create_app(config)
    with app.app_context():
        d = Detection(label="glass", confidence=0.9, model_version="mock")
        db.session.add(d)
        db.session.flush()
        db.session.add(Operation(detection_id=d.id, target_bin="glass", status="running", min_confidence=0.6, full_threshold=90))
        db.session.commit()

    restarted = create_app(config)
    with restarted.app_context():
        op = Operation.query.one()
        assert (op.status, op.reason) == ("failed", "interrupted")


def test_image_required_for_real_model(client, classifier):
    classifier.needs_image = True
    res = client.post("/api/detect")
    assert res.status_code == 400
    assert res.get_json()["code"] == "image_required"


def test_sim_faults_endpoint(client, world):
    assert client.put("/api/sim/faults", json={"faults": ["jam"]}).get_json() == {"faults": ["jam"]}
    assert world.faults == {"jam"}
    assert client.put("/api/sim/faults", json={"faults": ["yangın"]}).status_code == 400
    assert client.put("/api/sim/faults", json={"faults": []}).get_json() == {"faults": []}


def test_analysis_owns_cycle_until_prediction_is_saved(app, client, classifier):
    old = detect(client)
    entered, release = threading.Event(), threading.Event()
    result = []

    def slow_predict(image):
        entered.set()
        assert release.wait(3)
        return Prediction("glass", 0.95)

    classifier.predict = slow_predict

    def analyze():
        with app.test_client() as other:
            result.append(other.post("/api/detect").status_code)

    worker = threading.Thread(target=analyze)
    worker.start()
    try:
        assert entered.wait(3)
        assert sort(client, old["id"]).get_json()["code"] == "busy"
        assert client.post("/api/system/reset").status_code == 409
        assert client.post("/api/detect").status_code == 409
    finally:
        release.set()
        worker.join(3)
    assert result == [201]
    assert sort(client, old["id"]).get_json()["code"] == "stale"
    assert sort(client, detect_latest(client)["id"]).status_code == 201


def test_command_lock_released_after_invalid_image(client):
    import io
    assert client.post('/api/detect', data={'image': (io.BytesIO(b'bad'), 'bad.jpg')}).status_code == 400
    assert client.post('/api/detect').status_code == 201


def test_sim_faults_rejects_unhashable_values(client):
    assert client.put('/api/sim/faults', json={'faults': [{}]}).status_code == 400


def broken_sensor():
    raise OSError("Ultrasonik sensör yanıt vermiyor")


def test_unreadable_fill_sensor_blocks_only_that_bin(client, classifier, ctrl):
    ctrl.hw.fill_sensors["metal"].distance_cm = broken_sensor

    bins = {b["type"]: b for b in client.get("/api/bins").get_json()}
    assert bins["metal"]["fill"] is None and bins["metal"]["sensorOk"] is False
    assert bins["metal"]["updatedAt"] is not None  # son başarılı okumanın zamanı
    assert bins["glass"]["sensorOk"] is True

    system = client.get("/api/system").get_json()
    assert system["state"] == "idle" and system["fault"] is None

    classifier.next = Prediction("metal", 0.95)
    d = detect(client)
    assert d["blockedReason"] == "sensor_error"
    op = sort(client, d["id"]).get_json()["operation"]
    assert (op["status"], op["reason"]) == ("rejected", "sensor_error")

    classifier.next = Prediction("glass", 0.95)
    assert sort(client, detect(client)["id"]).get_json()["operation"]["status"] == "completed"


def test_presence_sensor_failure_is_reported_not_hidden(client, ctrl):
    ctrl.hw.presence.item_present = broken_sensor
    res = client.get("/api/system")
    assert res.status_code == 200  # panel arızayı gösterebilmeli
    body = res.get_json()
    assert body["itemPresent"] is None
    assert body["state"] == "fault"
    assert body["fault"]["code"] == "driver_error"


def test_sim_faults_readable_during_command(app, client):
    lock = app.extensions["command_lock"]
    lock.acquire()
    try:
        assert client.get("/api/sim/faults").status_code == 200
        assert client.put("/api/sim/faults", json={"faults": []}).status_code == 409
    finally:
        lock.release()
