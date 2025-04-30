import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_secret_key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:1212714@localhost/taxi'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

