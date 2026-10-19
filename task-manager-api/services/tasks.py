from models import Task, User, Category
from repositories.store import transaction
from services.errors import DomainError
from services.validation import task_data, integer, filters
from utils.clock import utc_now
from utils.constants import TEAM_ROLES


def require_owner(actor, user_id):
    if actor.role not in TEAM_ROLES and actor.id != user_id:
        raise DomainError('Permissão insuficiente', 403)


class TaskService:
    def __init__(self, repository):
        self.repo, self.session = repository, repository.session

    def require(self, task_id, actor):
        integer(task_id, 'ID')
        task = self.repo.get(Task, task_id)
        if task is None:
            raise DomainError('Task não encontrada', 404)
        require_owner(actor, task.user_id)
        return task

    def list(self, actor, params=None):
        options = filters(params or {})
        scope = None if actor.role in TEAM_ROLES else actor.id
        if 'user_id' in options:
            require_owner(actor, options['user_id'])
        return self.repo.tasks(options, scope)

    def validate_relations(self, values):
        for key, model, message in (('user_id', User, 'Usuário não encontrado'),
                                    ('category_id', Category, 'Categoria não encontrada')):
            if values.get(key) is not None and self.repo.get(model, values[key]) is None:
                raise DomainError(message, 404)

    def create(self, data, actor):
        values = task_data(data, creating=True)
        values.setdefault('description', '')
        if 'user_id' not in values and actor.role not in TEAM_ROLES:
            values['user_id'] = actor.id
        require_owner(actor, values.get('user_id'))
        with transaction(self.session):
            self.validate_relations(values)
            task = self.repo.add(Task(**values))
        return task

    def update(self, task_id, data, actor):
        values = task_data(data)
        with transaction(self.session):
            task = self.require(task_id, actor)
            if 'user_id' in values:
                require_owner(actor, values['user_id'])
            self.validate_relations(values)
            for key, value in values.items():
                setattr(task, key, value)
            task.updated_at = utc_now()
        return task

    def delete(self, task_id, actor):
        with transaction(self.session):
            self.repo.delete_task(self.require(task_id, actor))
