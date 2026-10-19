from flask import current_app
from loja.context import components
from loja.errors import DomainError
from loja.http import body, signer, require_owner
from loja.views.serializers import user


def list_users():
    return {'dados': [user(row) for row in components().users.list()], 'sucesso': True}


def get_user(id):
    require_owner(id)
    row = components().users.get(id)
    if row is None:
        raise DomainError('Usuário não encontrado', 404)
    return {'dados': user(row), 'sucesso': True}


def create_user():
    user_id = components().accounts.register(body())
    return {'dados': {'id': user_id}, 'sucesso': True}, 201


def login():
    row = components().accounts.login(body())
    data = {key: row[key] for key in ('id', 'nome', 'email', 'tipo')}
    return {'dados': data, 'sucesso': True, 'mensagem': 'Login OK',
            'token': signer().dumps({'sub': row['id']}), 'expires_in': current_app.config['TOKEN_MAX_AGE']}
