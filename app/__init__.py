from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config_object="config.DevelopmentConfig"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # init extensions
    db.init_app(app)

    # register blueprints
    from .route import bp as main_bp
    app.register_blueprint(main_bp)

    return app
