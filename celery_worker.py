import sys, os

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from run import app
from app import celery

if __name__ == "__main__":
    celery.start()
