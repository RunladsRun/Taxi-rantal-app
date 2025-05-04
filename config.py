import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_secret_key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:Ssccoott.03295085@localhost/CS 480 project'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

