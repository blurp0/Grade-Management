from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # import Flask-Migrate

db = SQLAlchemy()
migrate = Migrate()  # create migrate object

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

    # register blueprints
    from .route import bp as main_bp
    app.register_blueprint(main_bp)

    return app
