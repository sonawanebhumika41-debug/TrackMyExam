import os
from urllib.parse import quote_plus
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '1234')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'trackmyexam')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-key')
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
