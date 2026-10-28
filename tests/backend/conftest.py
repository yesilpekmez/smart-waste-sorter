import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app import create_app  # noqa: E402
from app.classifier import Prediction  # noqa: E402


class FixedClassifier:
    """Testlerde her seferinde aynı sonucu döndürür."""

    name = "fixed"
    version = "fixed-test"
    needs_image = False

    def __init__(self):
        self.next = Prediction("plastic", 0.94, (40, 20, 20, 60))

    def predict(self, image):
        return self.next


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
            "UPLOAD_DIR": tmp_path / "uploads",
            "SIM_TIME_SCALE": 0,
            "MODEL_PATH": str(tmp_path / "yok.pt"),  # testler eğitilmiş modele bağlı olmasın
        }
    )
    app.extensions["classifier"] = FixedClassifier()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def classifier(app):
    return app.extensions["classifier"]


@pytest.fixture
def ctrl(app):
    return app.extensions["controller"]


@pytest.fixture
def world(app):
    return app.extensions["controller"].hw.world
