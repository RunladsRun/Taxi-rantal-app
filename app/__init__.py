# ==== app/__init__.py ====
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

# Create app factory
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    # login_manager.init_app(app)

    with app.app_context():
        from . import routes

    return app