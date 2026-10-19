from loja.context import components
from loja.http import body, require_owner
from loja.services.validation import integer
from loja.services.reports import sales_report
from loja.views.serializers import order


def create_order():
    data = body()
    user_id = integer(data.get('usuario_id'), 'Usuario ID')
    require_owner(user_id)
    result = components().checkout.create(user_id, data.get('itens'))
    return {'dados': result, 'sucesso': True, 'mensagem': 'Pedido criado com sucesso'}, 201


def list_orders():
    rows = components().orders.list_with_items()
    return {'dados': [order(row, items) for row, items in rows], 'sucesso': True}


def user_orders(usuario_id):
    require_owner(usuario_id)
    rows = components().orders.list_with_items(usuario_id)
    return {'dados': [order(row, items) for row, items in rows], 'sucesso': True}


def update_status(pedido_id):
    components().checkout.set_status(pedido_id, body().get('status'))
    return {'sucesso': True, 'mensagem': 'Status atualizado'}


def report():
    return {'dados': sales_report(components().orders.sales_totals()), 'sucesso': True}
