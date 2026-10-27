from __future__ import annotations

import os

from flask import Flask

from .classifier import load_classifier
from .config import Config
from .models import Bin, db
from .routes import api

# Sensörler bağlanana kadar örnek doluluk değerleri
DEMO_FILL = {"plastic": 42, "paper": 28, "glass": 65, "metal": 82}


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    app.extensions["classifier"] = load_classifier(app.config["MODEL_PATH"])
    app.register_blueprint(api)

    with app.app_context():
        db.create_all()
        if Bin.query.count() == 0:
            db.session.add_all(Bin(type=t, fill=f) for t, f in DEMO_FILL.items())
            db.session.commit()

    return app
