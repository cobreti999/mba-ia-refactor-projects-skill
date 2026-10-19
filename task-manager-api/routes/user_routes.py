from flask import Blueprint
from controllers import users
from http_support import access


def blueprint():
    bp = Blueprint('users', __name__)
    for path, method, handler, mode in (
        ('/users', 'GET', users.listing, 'team'), ('/users', 'POST', users.create, 'optional'),
        ('/users/<int:user_id>', 'GET', users.detail, 'user'),
        ('/users/<int:user_id>', 'PUT', users.update, 'user'),
        ('/users/<int:user_id>', 'DELETE', users.delete, 'admin'),
        ('/users/<int:user_id>/tasks', 'GET', users.tasks, 'user'),
        ('/login', 'POST', users.login, 'public'),
    ):
        bp.add_url_rule(path, handler.__name__, access(mode)(handler) if mode != 'public' else handler, methods=[method])
    return bp
