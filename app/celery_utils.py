from celery import Celery


def make_celery(app=None):
    celery = Celery(__name__)
    if app:
        celery.conf.update(
            broker_url=app.config["CELERY_BROKER_URL"],
            result_backend=app.config["CELERY_RESULT_BACKEND"],
        )

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery
