from __future__ import annotations

import os
import threading

from flask import Flask

from .classifier import load_classifier
from .config import Config
from .control import create_controller, sync_bins
from .models import db
from .routes import api
from .sorting import recover_interrupted


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    app.extensions["command_lock"] = threading.Lock()
    app.extensions["classifier"] = load_classifier(app.config["MODEL_PATH"])
    app.extensions["controller"] = create_controller(app)
    app.register_blueprint(api)

    with app.app_context():
        db.create_all()
        recover_interrupted()
        sync_bins()

    return app
