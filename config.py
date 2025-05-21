# config.py
class Config:
    SQLALCHEMY_DATABASE_URI = (
        "mysql+pymysql://root:@localhost:3306/grade_manage"
        #            └─ empty password after the colon
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
