#!/usr/bin/env python3

import flask
from flask_cors import CORS
from flask_migrate import Migrate

import core
import forums
import rules
from core import db

migrate = Migrate()

PLUGINS = [
    core,
    forums,
    rules,
    ]


class Config(*(plug.Config for plug in PLUGINS if hasattr(plug, 'Config'))):
    pass


def create_app(config: str) -> flask.Flask:
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    print(app.config['INVITE_LIFETIME'])
    app.config.from_pyfile(config)
    print(app.config['INVITE_LIFETIME'])

    migrate.init_app(app, db)
    CORS(app)

    for plug in PLUGINS:
        plug.init_app(app)

    return app


app = create_app('config.py')

if __name__ == '__main__':
    app.run()
