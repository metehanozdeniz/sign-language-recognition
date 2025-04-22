import sys, os

# Proje kök dizinini PYTHONPATH'e ekleyelim
sys.path.insert(0, os.path.abspath("."))

# Artık app paketini proje kökünden import edebiliriz
from app import app, celery

# Celery worker'ı çalıştırmak için bu dosyayı kullanabilirsiniz.
# Örneğin, bu dosyayı şu şekilde çalıştırabilirsiniz:
# celery -A celery_worker.celery worker --loglevel=info

if __name__ == "__main__":
    celery.start()
