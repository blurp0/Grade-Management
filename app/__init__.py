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

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)   # initialize migrate with app and db

    from . import model

    # Don't call create_all() when using migrations
    # with app.app_context():
    #     db.create_all()

    login_manager.init_app(app)      # initialize Flask-Login
    login_manager.login_view = "auth.login"  # route name for login page

    # register blueprints
    from .route import bp as main_bp
    app.register_blueprint(main_bp)

    return app
