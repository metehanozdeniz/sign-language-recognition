from app import create_app, celery

app = create_app()
celery.conf.update(app.config)

if __name__ == "__main__":
    celery.start()
