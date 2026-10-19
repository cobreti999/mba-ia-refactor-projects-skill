from datetime import datetime
import re
from services.errors import DomainError
from utils.constants import (VALID_STATUSES, VALID_ROLES, MIN_TITLE_LENGTH, MAX_TITLE_LENGTH,
                             MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH, MAX_ID)


def text(value, name, minimum=1, maximum=None, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or (minimum and not value.strip()):
        raise DomainError(f'{name} deve ser texto válido')
    if len(value) < minimum or (maximum is not None and len(value) > maximum):
        raise DomainError(f'{name} tem comprimento inválido')
    return value


def integer(value, name, maximum=MAX_ID, nullable=False):
    if value is None and nullable:
        return None
    if type(value) is not int or not 1 <= value <= maximum:
        raise DomainError(f'{name} deve ser inteiro entre 1 e {maximum}')
    return value


def choice(value, name, choices):
    if not isinstance(value, str) or value not in choices:
        raise DomainError(f'{name} inválido')
    return value


def password(value):
    return text(value, 'Senha', MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH)


def email(value):
    value = text(value, 'Email', maximum=150)
    if not re.fullmatch(r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+', value):
        raise DomainError('Email inválido')
    return value


def user_data(data, creating=False):
    result = {}
    for key, validator in {
        'name': lambda v: text(v, 'Nome', maximum=100),
        'email': email, 'password': password,
        'role': lambda v: choice(v, 'Role', VALID_ROLES),
    }.items():
        if key in data or (creating and key in ('name', 'email', 'password')):
            result[key] = validator(data.get(key))
    if 'active' in data:
        if type(data['active']) is not bool:
            raise DomainError('Active deve ser booleano')
        result['active'] = data['active']
    return result


def task_data(data, creating=False):
    result = {}
    if 'title' in data or creating:
        result['title'] = text(data.get('title'), 'Título', MIN_TITLE_LENGTH, MAX_TITLE_LENGTH)
    if 'description' in data:
        result['description'] = text(data['description'], 'Descrição', 0, nullable=True)
    if 'status' in data:
        result['status'] = choice(data['status'], 'Status', VALID_STATUSES)
    if 'priority' in data:
        result['priority'] = integer(data['priority'], 'Prioridade', 5)
    for key in ('user_id', 'category_id'):
        if key in data:
            result[key] = integer(data[key], key, nullable=True)
    if 'due_date' in data:
        value = data['due_date']
        if value is None or value == '':
            result['due_date'] = None
        else:
            text(value, 'Data')
            try:
                result['due_date'] = datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                raise DomainError('Formato de data inválido. Use YYYY-MM-DD') from None
    if 'tags' in data:
        value = data['tags']
        if isinstance(value, list):
            if any(not isinstance(tag, str) for tag in value):
                raise DomainError('Tags devem conter somente textos')
            value = ','.join(value)
        result['tags'] = text(value, 'Tags', 0, 500, nullable=True)
    return result


def category_data(data, creating=False):
    result = {}
    if 'name' in data or creating:
        result['name'] = text(data.get('name'), 'Nome', maximum=100)
    if 'description' in data:
        result['description'] = text(data['description'], 'Descrição', 0, 300, nullable=True)
    if 'color' in data:
        color = text(data['color'], 'Cor')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise DomainError('Cor deve usar #RRGGBB')
        result['color'] = color
    return result


def filters(data):
    result = {}
    for key, maximum in (('priority', 5), ('user_id', MAX_ID)):
        value = data.get(key, '')
        if value != '':
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise DomainError(f'{key} deve ser inteiro') from None
            result[key] = integer(value, key, maximum)
    if data.get('status', '') != '':
        result['status'] = choice(data['status'], 'Status', VALID_STATUSES)
    result['q'] = text(data.get('q', ''), 'Busca', 0)
    return result
