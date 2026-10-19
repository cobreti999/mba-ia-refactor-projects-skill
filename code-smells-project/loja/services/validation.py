import math
from loja.errors import DomainError

CATEGORIES = ('informatica', 'moveis', 'vestuario', 'geral', 'eletronicos', 'livros')
ORDER_STATUSES = ('pendente', 'aprovado', 'enviado', 'entregue', 'cancelado')
MIN_PRODUCT_NAME = 2
MAX_PRODUCT_NAME = 200


def text(value, name, minimum=1, maximum=None):
    if not isinstance(value, str) or len(value) < minimum or (maximum is not None and len(value) > maximum):
        raise DomainError(f'{name} inválido')
    return value


def integer(value, name, minimum=1):
    if type(value) is not int or value < minimum or value > 9223372036854775807:
        raise DomainError(f'{name} deve ser inteiro maior ou igual a {minimum}')
    return value


def number(value, name):
    if type(value) not in (int, float):
        raise DomainError(f'{name} inválido')
    try:
        valid = math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise DomainError(f'{name} inválido')
    return value


def product_data(data):
    name = text(data.get('nome'), 'Nome', MIN_PRODUCT_NAME, MAX_PRODUCT_NAME)
    category = text(data.get('categoria', 'geral'), 'Categoria')
    if category not in CATEGORIES:
        raise DomainError('Categoria inválida')
    return {'nome': name, 'descricao': text(data.get('descricao', ''), 'Descrição', minimum=0),
            'preco': number(data.get('preco'), 'Preço'),
            'estoque': integer(data.get('estoque'), 'Estoque', minimum=0), 'categoria': category}


def price_filter(raw):
    if raw is None or raw == '':
        return None
    try:
        value = float(raw)
    except (ValueError, TypeError):
        raise DomainError('Filtro de preço inválido') from None
    return number(value, 'Filtro de preço')


def order_items(items):
    if not isinstance(items, list) or not items:
        raise DomainError('Pedido deve ter pelo menos 1 item')
    consolidated = {}
    for item in items:
        if not isinstance(item, dict):
            raise DomainError('Item inválido')
        product_id = integer(item.get('produto_id'), 'Produto ID')
        quantity = integer(item.get('quantidade'), 'Quantidade')
        consolidated[product_id] = integer(consolidated.get(product_id, 0) + quantity, 'Quantidade')
    return consolidated
