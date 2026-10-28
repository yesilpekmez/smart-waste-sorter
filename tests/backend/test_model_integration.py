"""Gerçek YOLO modeliyle fotoğraf → tahmin → kayıt akışı.

Eğitilmiş ağırlıklar ve ultralytics kurulu değilse atlanır.
"""
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = ROOT / "ai" / "weights" / "best.pt"
TEST_IMAGES = ROOT / "ai" / "datasets" / "trashnet" / "test"

pytest.importorskip("ultralytics")
pytestmark = pytest.mark.skipif(not WEIGHTS.is_file(), reason="eğitilmiş model yok")


@pytest.fixture
def real_client(tmp_path):
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'real.db'}",
            "UPLOAD_DIR": tmp_path / "uploads",
            "SIM_TIME_SCALE": 0,
            "MODEL_PATH": str(WEIGHTS),
        }
    )
    assert app.extensions["classifier"].name == "yolo"
    return app.test_client()


@pytest.mark.skipif(not TEST_IMAGES.is_dir(), reason="TrashNet test kümesi hazırlanmamış")
@pytest.mark.parametrize("label", ["glass", "metal", "paper", "plastic"])
def test_real_model_classifies_and_records(real_client, label):
    image = sorted((TEST_IMAGES / label).glob("*.jpg"))[0]
    res = real_client.post("/api/detect", data={"image": (io.BytesIO(image.read_bytes()), image.name)})
    assert res.status_code == 201
    body = res.get_json()
    assert body["label"] in {"glass", "metal", "paper", "plastic"}
    assert body["modelVersion"].startswith("best-")
    assert real_client.get(body["imageUrl"]).status_code == 200

    op = real_client.post("/api/sort", json={"detectionId": body["id"]}).get_json()["operation"]
    assert op["status"] in {"completed", "rejected"}


def test_real_model_requires_image(real_client):
    assert real_client.post("/api/detect").status_code == 400
