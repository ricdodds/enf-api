import os
import logging

from flask import Flask
from celery import Celery, Task


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        CELERY=dict(
            broker_url=os.getenv('REDIS_URL', 'redis://localhost'),
            result_backend=os.getenv('REDIS_URL', 'redis://localhost'),
            task_ignore_result=True,
        ),
    )
    app.config.from_prefixed_env()
    celery_init_app(app)

    @app.route("/")
    def index() -> str:
        return "ENF API"

    from . import match, datasets

    app.register_blueprint(match.bp)
    app.register_blueprint(datasets.bp)

    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

    return app


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app

    return celery_app
