from pathlib import Path
import os

from flask import Flask

from .db import init_db
from .auth import bp as auth_bp
from .routes import bp


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SPEAKTRAIN_SECRET_KEY", "speaktrain-local-development-only"),
        DATABASE=os.environ.get("SPEAKTRAIN_DATABASE", str(Path(app.instance_path) / "speaktrain.sqlite3")),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path, "audio").mkdir(parents=True, exist_ok=True)
    init_db(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(bp)
    return app
