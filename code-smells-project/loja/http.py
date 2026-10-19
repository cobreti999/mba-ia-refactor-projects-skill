from functools import wraps
from uuid import uuid4
from flask import current_app, g, request
from itsdangerous import URLSafeTimedSerializer, BadData
from werkzeug.exceptions import HTTPException
from loja.context import components
from loja.errors import DomainError


def body():
    if not request.is_json:
        raise DomainError('Corpo deve ser um objeto JSON')
    data = request.get_json()
    if not isinstance(data, dict) or not data:
        raise DomainError('Dados inválidos')
    return data


def signer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='loja-auth-v1')


def require_user(admin=False):
    def decorate(handler):
        @wraps(handler)
        def protected(*args, **kwargs):
            parts = request.headers.get('Authorization', '').split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                raise DomainError('Autenticação necessária', 401)
            try:
                data = signer().loads(parts[1], max_age=current_app.config['TOKEN_MAX_AGE'])
                if not isinstance(data, dict) or type(data.get('sub')) is not int:
                    raise BadData('Invalid identity')
            except BadData:
                raise DomainError('Token inválido ou expirado', 401) from None
            identity = components().users.get(data['sub'])
            if identity is None:
                raise DomainError('Token inválido ou expirado', 401)
            if admin and identity['tipo'] != 'admin':
                raise DomainError('Permissão insuficiente', 403)
            g.identity = identity
            return handler(*args, **kwargs)
        return protected
    return decorate


def require_owner(user_id):
    if g.identity['tipo'] != 'admin' and g.identity['id'] != user_id:
        raise DomainError('Permissão insuficiente', 403)


def register_errors(app):
    @app.errorhandler(DomainError)
    def domain_error(error):
        return {'erro': error.message, 'sucesso': False}, error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {400: 'Requisição inválida', 404: 'Recurso não encontrado',
                    405: 'Método não permitido', 413: 'Corpo muito grande', 415: 'Formato não suportado'}
        response = error.get_response()
        response.data = app.json.dumps({'erro': messages.get(error.code, error.name), 'sucesso': False})
        response.content_type = 'application/json'
        return response

    @app.errorhandler(Exception)
    def unexpected(error):
        reference = uuid4().hex
        # Não registrar str(error): mensagens de drivers podem conter dados de entrada/SQL.
        app.logger.error('unexpected_error type=%s reference=%s', type(error).__name__, reference)
        return {'erro': 'Erro interno', 'sucesso': False, 'referencia': reference}, 500
