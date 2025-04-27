import os


basedir = os.path.abspath(os.path.dirname(__file__))

VIDEO_DIR = os.path.join(basedir, "videos")

if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "gizli_anahtar"
    # ek ayarlar (DB URI vb.)
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        basedir, "sign-language-recognition.sqlite"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CELERY_BROKER_URL = "redis://localhost:6379/0"
    # CELERY_BROKER_URL = "rediss://:p94f5b8254a375717cceef3e88703d824469d08b8a5a8d2aa7e6b1f49efae6d79@ec2-52-72-19-75.compute-1.amazonaws.com:6769"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
