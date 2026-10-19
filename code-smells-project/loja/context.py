"""Composição por contexto; domínio e repositories não importam Flask."""
from types import SimpleNamespace
from flask import current_app, g
from loja.database import connect
from loja.models.products import ProductRepository
from loja.models.users import UserRepository
from loja.models.orders import OrderRepository
from loja.models.admin import AdminRepository
from loja.services.accounts import AccountService
from loja.services.orders import OrderService


def components():
    if 'components' not in g:
        connection = connect(current_app.config['DATABASE'])
        g.connection = connection
        products, users, orders = ProductRepository(connection), UserRepository(connection), OrderRepository(connection)
        g.components = SimpleNamespace(
            connection=connection, products=products, users=users, orders=orders,
            admin=AdminRepository(connection), accounts=AccountService(connection, users),
            checkout=OrderService(connection, products, users, orders),
        )
    return g.components


def close_connection(error=None):
    connection = g.pop('connection', None)
    if connection is not None:
        connection.close()
    g.pop('components', None)
