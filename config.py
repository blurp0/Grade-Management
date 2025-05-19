# config.py
class Config:
    SECRET_KEY = "change-me"
    SQLALCHEMY_DATABASE_URI = "sqlite:///grades.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
