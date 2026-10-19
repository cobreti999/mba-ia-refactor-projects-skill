from flask import Flask
from flask_cors import CORS
from loja.config import load_config
from loja.context import close_connection
from loja.http import register_errors
from loja.routes import register_routes
from loja.cli import register_commands


def create_app(overrides=None):
    app = Flask(__name__, static_folder=None)
    app.config.from_mapping(load_config(overrides))
    CORS(app, origins=app.config['CORS_ORIGINS'])
    app.teardown_appcontext(close_connection)
    register_errors(app)
    register_routes(app)
    register_commands(app)
    return app
