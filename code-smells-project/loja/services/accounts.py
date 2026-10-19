from werkzeug.security import generate_password_hash, check_password_hash
from loja.database import transaction
from loja.errors import DomainError
from loja.services.validation import text


class AccountService:
    def __init__(self, connection, users):
        self.connection, self.users = connection, users

    def register(self, data, role='cliente'):
        name = text(data.get('nome'), 'Nome')
        email = text(data.get('email'), 'Email')
        password = text(data.get('senha'), 'Senha')
        hashed = generate_password_hash(password)
        with transaction(self.connection):
            if self.users.by_email(email):
                raise DomainError('Email já cadastrado', 409)
            return self.users.create(name, email, hashed, role)

    def login(self, data):
        email = text(data.get('email'), 'Email')
        password = text(data.get('senha'), 'Senha')
        user = self.users.by_email(email)
        if user is None or user['senha_format'] != 'werkzeug':
            raise DomainError('Email ou senha inválidos', 401)
        try:
            valid = check_password_hash(user['senha'], password)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise DomainError('Email ou senha inválidos', 401)
        return user

    def migrate_passwords(self):
        with transaction(self.connection):
            users = self.users.legacy_passwords()
            for user in users:
                if not isinstance(user['senha'], str):
                    raise DomainError('Senha legada inválida; migração revertida')
                self.users.set_password_hash(user['id'], generate_password_hash(user['senha']))
        return len(users)
