#!/usr/bin/env python3

import flask
from flask_cors import CORS
from flask_migrate import Migrate

import core
import forums
import rules
import messages
from core import db

migrate = Migrate()

PLUGINS = [
    core,
    forums,
    rules,
    messages,
    ]


class Config(*(plug.Config for plug in PLUGINS if hasattr(plug, 'Config'))):
    pass


def create_app(config: str) -> flask.Flask:
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    app.config.from_pyfile(config)

    migrate.init_app(app, db)
    CORS(app)

    for plug in PLUGINS:
        plug.init_app(app)

    return app


app = create_app('config.py')

if __name__ == '__main__':
    app.run()
