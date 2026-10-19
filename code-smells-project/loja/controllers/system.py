from flask import current_app
from loja.context import components
from loja.database import transaction
from loja.errors import DomainError
from loja.http import body


def index():
    return {'mensagem': 'Bem-vindo à API da Loja', 'versao': '1.0.0', 'endpoints': {
        'produtos': '/produtos', 'usuarios': '/usuarios', 'pedidos': '/pedidos',
        'login': '/login', 'relatorios': '/relatorios/vendas', 'health': '/health'}}


def health():
    return {'status': 'ok', 'database': 'connected', 'counts': components().admin.counts(), 'versao': '1.0.0'}


def query():
    data = body()
    if set(data) != {'operacao'} or data['operacao'] != 'contagens':
        raise DomainError('Use somente a operação contagens; SQL livre não é permitido')
    return {'dados': components().admin.counts(), 'sucesso': True}


def reset():
    if not current_app.config['ALLOW_DB_RESET']:
        raise DomainError('Reset desabilitado', 403)
    ctx = components()
    with transaction(ctx.connection):
        ctx.admin.reset()
    return {'mensagem': 'Banco de dados resetado', 'sucesso': True}
