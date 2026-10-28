import io

from PIL import Image

from app.classifier import Prediction


def fill_of(client, bin_type):
    return next(b["fill"] for b in client.get("/api/bins").get_json() if b["type"] == bin_type)


def test_bins_are_seeded(client):
    bins = client.get("/api/bins").get_json()
    assert [b["type"] for b in bins] == ["plastic", "paper", "glass", "metal"]


def test_detect_with_image_saves_frame(client):
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), "white").save(buf, "PNG")
    buf.seek(0)

    res = client.post("/api/detect", data={"image": (buf, "atik.png")})
    assert res.status_code == 201
    body = res.get_json()
    assert body["label"] == "plastic"
    assert body["blockedReason"] is None

    image = client.get(body["imageUrl"])
    assert image.status_code == 200
    assert image.mimetype == "image/jpeg"


def test_detect_rejects_invalid_image(client):
    res = client.post("/api/detect", data={"image": (io.BytesIO(b"not an image"), "x.png")})
    assert res.status_code == 400


def test_sort_completes_and_fills_bin(client):
    before = fill_of(client, "plastic")
    detection = client.post("/api/detect").get_json()

    res = client.post("/api/sort", json={"detectionId": detection["id"]})
    assert res.status_code == 201
    assert res.get_json()["operation"]["status"] == "completed"
    assert fill_of(client, "plastic") > before


def test_sort_twice_is_rejected(client):
    detection = client.post("/api/detect").get_json()
    client.post("/api/sort", json={"detectionId": detection["id"]})
    assert client.post("/api/sort", json={"detectionId": detection["id"]}).status_code == 409


def test_uncertain_prediction_is_not_sorted(client, classifier):
    classifier.next = Prediction("glass", 0.45, (40, 20, 20, 60))
    before = fill_of(client, "glass")
    detection = client.post("/api/detect").get_json()
    assert detection["blockedReason"] == "uncertain"

    op = client.post("/api/sort", json={"detectionId": detection["id"]}).get_json()["operation"]
    assert (op["status"], op["reason"]) == ("rejected", "uncertain")
    assert fill_of(client, "glass") == before


def test_full_bin_blocks_sorting_until_emptied(client, classifier, app):
    app.config["FULL_THRESHOLD"] = 80  # metal %82 ile başlıyor
    classifier.next = Prediction("metal", 0.95, (40, 20, 20, 60))

    detection = client.post("/api/detect").get_json()
    assert detection["blockedReason"] == "bin_full"

    client.post("/api/bins/metal/empty")
    assert client.get("/api/detections/latest").get_json()["blockedReason"] is None


def test_operations_newest_first(client):
    for _ in range(3):
        d = client.post("/api/detect").get_json()
        client.post("/api/sort", json={"detectionId": d["id"]})
    body = client.get("/api/operations?limit=2").get_json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["items"][0]["id"] > body["items"][1]["id"]


def test_classification_result_has_no_box(client, classifier):
    classifier.next = Prediction("paper", 0.9)
    body = client.post("/api/detect").get_json()
    assert body["box"] is None
    assert body["label"] == "paper"


def test_jam_records_failed_operation_and_blocks_until_reset(client, world):
    world.faults.add("jam")
    d = client.post("/api/detect").get_json()
    op = client.post("/api/sort", json={"detectionId": d["id"]}).get_json()["operation"]
    assert (op["status"], op["reason"]) == ("failed", "jam")
    assert client.get("/api/system").get_json()["state"] == "fault"

    d2 = client.post("/api/detect").get_json()
    res = client.post("/api/sort", json={"detectionId": d2["id"]})
    assert res.status_code == 409
    assert res.get_json()["code"] == "faulted"

    world.faults.clear()
    assert client.post("/api/system/reset").get_json()["state"] == "idle"
    assert client.post("/api/sort", json={"detectionId": d2["id"]}).status_code == 201


def test_empty_bin_resets_sensor_reading(client):
    assert client.post("/api/bins/metal/empty").get_json()["fill"] == 0
    assert fill_of(client, "metal") == 0


def test_operations_filter_and_stats(client, classifier):
    for pred in [Prediction("glass", 0.9), Prediction("glass", 0.4), Prediction("paper", 0.95)]:
        classifier.next = pred
        d = client.post("/api/detect").get_json()
        client.post("/api/sort", json={"detectionId": d["id"]})

    glass = client.get("/api/operations?label=glass").get_json()
    assert glass["total"] == 2
    rejected = client.get("/api/operations?status=rejected").get_json()
    assert [o["label"] for o in rejected["items"]] == ["glass"]

    stats = client.get("/api/stats").get_json()
    assert (stats["total"], stats["completed"], stats["rejected"]) == (3, 2, 1)
    assert stats["byClass"]["glass"] == {"completed": 1, "rejected": 1, "aborted": 0, "failed": 0}
