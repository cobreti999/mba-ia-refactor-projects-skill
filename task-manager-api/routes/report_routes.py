from flask import Blueprint
from controllers import reports
from http_support import access


def blueprint():
    bp = Blueprint('reports', __name__)
    for path, method, handler, mode in (
        ('/reports/summary', 'GET', reports.summary, 'team'),
        ('/reports/user/<int:user_id>', 'GET', reports.user, 'user'),
        ('/categories', 'GET', reports.categories, 'user'),
        ('/categories', 'POST', reports.create_category, 'team'),
        ('/categories/<int:cat_id>', 'PUT', reports.update_category, 'team'),
        ('/categories/<int:cat_id>', 'DELETE', reports.delete_category, 'team'),
    ):
        bp.add_url_rule(path, handler.__name__, access(mode)(handler), methods=[method])
    return bp
