from loja.controllers import products, users, orders, system
from loja.http import require_user


def register_routes(app):
    routes = [
        ('GET', '/', system.index, 'index', 'public'),
        ('GET', '/health', system.health, 'health_check', 'public'),
        ('GET', '/produtos', products.list_products, 'listar_produtos', 'public'),
        ('GET', '/produtos/busca', products.search_products, 'buscar_produtos', 'public'),
        ('GET', '/produtos/<int:id>', products.get_product, 'buscar_produto', 'public'),
        ('POST', '/produtos', products.create_product, 'criar_produto', 'admin'),
        ('PUT', '/produtos/<int:id>', products.update_product, 'atualizar_produto', 'admin'),
        ('DELETE', '/produtos/<int:id>', products.delete_product, 'deletar_produto', 'admin'),
        ('GET', '/usuarios', users.list_users, 'listar_usuarios', 'admin'),
        ('GET', '/usuarios/<int:id>', users.get_user, 'buscar_usuario', 'user'),
        ('POST', '/usuarios', users.create_user, 'criar_usuario', 'public'),
        ('POST', '/login', users.login, 'login', 'public'),
        ('POST', '/pedidos', orders.create_order, 'criar_pedido', 'user'),
        ('GET', '/pedidos', orders.list_orders, 'listar_todos_pedidos', 'admin'),
        ('GET', '/pedidos/usuario/<int:usuario_id>', orders.user_orders, 'listar_pedidos_usuario', 'user'),
        ('PUT', '/pedidos/<int:pedido_id>/status', orders.update_status, 'atualizar_status_pedido', 'admin'),
        ('GET', '/relatorios/vendas', orders.report, 'relatorio_vendas', 'admin'),
        ('POST', '/admin/query', system.query, 'executar_query', 'admin'),
        ('POST', '/admin/reset-db', system.reset, 'reset_database', 'admin'),
    ]
    for method, path, handler, endpoint, access in routes:
        if access != 'public':
            handler = require_user(admin=access == 'admin')(handler)
        app.add_url_rule(path, endpoint, handler, methods=[method])
