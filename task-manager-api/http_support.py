import hashlib
import hmac
from functools import wraps
from uuid import uuid4
from flask import current_app, request, g
from itsdangerous import URLSafeTimedSerializer, BadData
from werkzeug.exceptions import HTTPException
from context import components
from database import db
from models import User
from services.errors import DomainError
from utils.constants import VALID_ROLES


def body():
    if not request.is_json:
        raise DomainError('Corpo deve ser um objeto JSON')
    data = request.get_json()
    if not isinstance(data, dict) or not data:
        raise DomainError('Dados inválidos')
    return data


def signer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='task-manager-auth-v1')


def credential_stamp(user):
    # Invalida tokens após troca/reset de senha, sem expor o hash armazenado.
    return hmac.new(current_app.config['SECRET_KEY'].encode(), user.password.encode(), hashlib.sha256).hexdigest()


def issue_token(user):
    return signer().dumps({'sub': user.id, 'stamp': credential_stamp(user)})


def authenticate(optional=False):
    header = request.headers.get('Authorization')
    if optional and header is None:
        g.actor = None
        return
    parts = (header or '').split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise DomainError('Autenticação necessária', 401)
    try:
        data = signer().loads(parts[1], max_age=current_app.config['TOKEN_MAX_AGE'])
        if not isinstance(data, dict) or type(data.get('sub')) is not int or not isinstance(data.get('stamp'), str):
            raise BadData('Invalid identity')
    except BadData:
        raise DomainError('Token inválido ou expirado', 401) from None
    user = components().repository.get(User, data['sub'])
    if user is None or not user.active or user.role not in VALID_ROLES:
        raise DomainError('Token inválido ou expirado', 401)
    if not hmac.compare_digest(data['stamp'], credential_stamp(user)):
        raise DomainError('Token inválido ou expirado', 401)
    g.actor = user


def access(mode):
    def decorate(handler):
        @wraps(handler)
        def guarded(*args, **kwargs):
            authenticate(optional=mode == 'optional')
            if mode == 'admin' and g.actor.role != 'admin':
                raise DomainError('Permissão insuficiente', 403)
            if mode == 'team' and g.actor.role not in ('admin', 'manager'):
                raise DomainError('Permissão insuficiente', 403)
            return handler(*args, **kwargs)
        return guarded
    return decorate


def register_errors(app):
    @app.errorhandler(DomainError)
    def known(error):
        db.session.rollback()
        return {'error': error.message}, error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        db.session.rollback()
        messages = {400: 'Requisição inválida', 404: 'Recurso não encontrado',
                    405: 'Método não permitido', 413: 'Corpo muito grande', 415: 'Formato não suportado'}
        response = error.get_response()
        response.data = app.json.dumps({'error': messages.get(error.code, error.name)})
        response.content_type = 'application/json'
        return response

    @app.errorhandler(Exception)
    def unexpected(error):
        db.session.rollback()
        reference = uuid4().hex
        app.logger.error('unexpected_error type=%s reference=%s', type(error).__name__, reference)
        return {'error': 'Erro interno', 'reference': reference}, 500
