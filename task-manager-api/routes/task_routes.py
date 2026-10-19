from flask import Blueprint
from controllers import tasks
from http_support import access


def blueprint():
    bp = Blueprint('tasks', __name__)
    for path, method, handler in (
        ('/tasks', 'GET', tasks.listing), ('/tasks', 'POST', tasks.create),
        ('/tasks/<int:task_id>', 'GET', tasks.detail), ('/tasks/<int:task_id>', 'PUT', tasks.update),
        ('/tasks/<int:task_id>', 'DELETE', tasks.delete), ('/tasks/search', 'GET', tasks.search),
        ('/tasks/stats', 'GET', tasks.stats),
    ):
        bp.add_url_rule(path, handler.__name__, access('user')(handler), methods=[method])
    return bp
