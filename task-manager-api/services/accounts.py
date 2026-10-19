from sqlalchemy.exc import IntegrityError
from models import User
from services.errors import DomainError
from services.validation import user_data, text, email, password, integer
from repositories.store import transaction


class AccountService:
    def __init__(self, repository):
        self.repo, self.session = repository, repository.session

    def require(self, user_id):
        integer(user_id, 'ID')
        user = self.repo.get(User, user_id)
        if user is None:
            raise DomainError('Usuário não encontrado', 404)
        return user

    def create(self, data, privileged=False):
        values = user_data(data, creating=True)
        if not privileged and (values.get('role', 'user') != 'user' or 'active' in values):
            raise DomainError('Permissão insuficiente', 403)
        try:
            with transaction(self.session):
                if self.repo.by_email(values['email']):
                    raise DomainError('Email já cadastrado', 409)
                user = User(name=values['name'], email=values['email'], role=values.get('role', 'user'),
                            active=values.get('active', True))
                user.set_password(values['password'])
                self.repo.add(user)
        except IntegrityError as error:
            if 'users.email' in str(error.orig):
                raise DomainError('Email já cadastrado', 409) from None
            raise
        return user

    def update(self, user_id, data, actor):
        if actor.role != 'admin' and actor.id != user_id:
            raise DomainError('Permissão insuficiente', 403)
        values = user_data(data)
        if actor.role != 'admin' and ('role' in values or 'active' in values):
            raise DomainError('Permissão insuficiente', 403)
        try:
            with transaction(self.session):
                user = self.require(user_id)
                if 'email' in values:
                    other = self.repo.by_email(values['email'])
                    if other and other.id != user.id:
                        raise DomainError('Email já cadastrado', 409)
                for key, value in values.items():
                    if key == 'password':
                        user.set_password(value)
                    else:
                        setattr(user, key, value)
        except IntegrityError as error:
            if 'users.email' in str(error.orig):
                raise DomainError('Email já cadastrado', 409) from None
            raise
        return user

    def login(self, data):
        address = email(data.get('email'))
        candidate = text(data.get('password'), 'Senha', maximum=128)
        user = self.repo.by_email(address)
        if user is None or not user.check_password(candidate):
            raise DomainError('Credenciais inválidas', 401)
        if not user.active:
            raise DomainError('Usuário inativo', 403)
        return user

    def reset_password(self, user_id, value):
        value = password(value)
        with transaction(self.session):
            user = self.require(user_id)
            user.set_password(value)

    def delete(self, user_id):
        with transaction(self.session):
            self.repo.delete_user(self.require(user_id))
