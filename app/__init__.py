import secrets
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # import Flask-Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()  # create migrate object
login_manager = LoginManager()

def create_app(config_object="config.DevelopmentConfig"):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.secret_key = secrets.token_hex(16)

    db.init_app(app)
    # Comment out or remove migrate
    # migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "main.home"

    from .route import bp as main_bp
    app.register_blueprint(main_bp)

    # Create tables directly (not recommended for production, but okay for dev)
    with app.app_context():
        db.create_all()

    return app

