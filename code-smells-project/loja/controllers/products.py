from flask import request
from loja.context import components
from loja.database import transaction
from loja.errors import DomainError
from loja.http import body
from loja.services.validation import product_data, price_filter
from loja.views.serializers import product


def require_product(repository, product_id):
    row = repository.get(product_id)
    if row is None:
        raise DomainError('Produto não encontrado', 404)
    return row


def list_products():
    return {'dados': [product(row) for row in components().products.list()], 'sucesso': True}


def get_product(id):
    return {'dados': product(require_product(components().products, id)), 'sucesso': True}


def search_products():
    minimum = price_filter(request.args.get('preco_min'))
    maximum = price_filter(request.args.get('preco_max'))
    if minimum is not None and maximum is not None and minimum > maximum:
        raise DomainError('Faixa de preço inválida')
    rows = components().products.list(request.args.get('q', ''), request.args.get('categoria'), minimum, maximum)
    return {'dados': [product(row) for row in rows], 'total': len(rows), 'sucesso': True}


def create_product():
    data, ctx = product_data(body()), components()
    with transaction(ctx.connection):
        product_id = ctx.products.create(data)
    return {'dados': {'id': product_id}, 'sucesso': True, 'mensagem': 'Produto criado'}, 201


def update_product(id):
    data, ctx = product_data(body()), components()
    with transaction(ctx.connection):
        require_product(ctx.products, id)
        ctx.products.update(id, data)
    return {'sucesso': True, 'mensagem': 'Produto atualizado'}


def delete_product(id):
    ctx = components()
    with transaction(ctx.connection):
        require_product(ctx.products, id)
        ctx.products.delete(id)
    return {'sucesso': True, 'mensagem': 'Produto deletado'}
