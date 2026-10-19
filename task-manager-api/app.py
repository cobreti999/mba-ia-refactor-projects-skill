import os
from flask import Flask
from flask_cors import CORS
from sqlalchemy import event
from config import load_config
from database import db
from http_support import register_errors
from utils.clock import utc_now


def sqlite_constraints(connection, _record):
    cursor = connection.cursor()
    try:
        cursor.execute('PRAGMA foreign_keys=ON')
    finally:
        cursor.close()


def create_app(overrides=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(load_config(overrides))
    CORS(app, origins=app.config['CORS_ORIGINS'])
    db.init_app(app)
    with app.app_context():
        if db.engine.dialect.name == 'sqlite':
            event.listen(db.engine, 'connect', sqlite_constraints)
    from routes.task_routes import blueprint as tasks
    from routes.user_routes import blueprint as users
    from routes.report_routes import blueprint as reports
    from cli import register_commands
    app.register_blueprint(tasks())
    app.register_blueprint(users())
    app.register_blueprint(reports())
    register_errors(app)
    register_commands(app)
    app.add_url_rule('/', 'index', lambda: {'message': 'Task Manager API', 'version': '1.0'})
    app.add_url_rule('/health', 'health', lambda: {'status': 'ok', 'timestamp': str(utc_now())})
    return app


if __name__ == '__main__':
    port = int(os.environ.get('TASK_PORT', '5000'))
    if not 0 <= port <= 65535:
        raise RuntimeError('TASK_PORT deve estar entre 0 e 65535')
    create_app().run(host=os.environ.get('TASK_HOST', '127.0.0.1'), port=port, debug=False, use_reloader=False)
