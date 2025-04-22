import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask
from app.config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Celery entegrasyonu: make_celery fonksiyonunu app/celery_utils.py'den içeri aktarıyoruz.
from app.celery_utils import make_celery

celery = make_celery(app)

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

db_path = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "sign-language-recognition.sqlite"
)

if not os.path.exists(db_path):
    with app.app_context():
        db.create_all()
        print("Database created.")
else:
    print("Database exists.")

from app import routes, models, forms
