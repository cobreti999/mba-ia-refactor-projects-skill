from flask import g, current_app
from context import components
from http_support import body, issue_token
from services.tasks import require_owner
from utils.clock import utc_now
from views.serializers import user_public, task_public, task_for_user


def listing():
    return [{**user_public(user), 'task_count': total}
            for user, total, _ in components().repository.users_with_counts()]


def detail(user_id):
    require_owner(g.actor, user_id)
    user = components().accounts.require(user_id)
    return {**user_public(user), 'tasks': [task_public(task) for task in
            components().repository.tasks({'user_id': user.id})]}


def create():
    return user_public(components().accounts.create(body(), privileged=bool(g.actor and g.actor.is_admin()))), 201


def update(user_id):
    return user_public(components().accounts.update(user_id, body(), g.actor))


def delete(user_id):
    components().accounts.delete(user_id)
    return {'message': 'Usuário deletado com sucesso'}


def tasks(user_id):
    require_owner(g.actor, user_id)
    components().accounts.require(user_id)
    now = utc_now()
    return [task_for_user(task, now) for task in components().repository.tasks({'user_id': user_id})]


def login():
    user = components().accounts.login(body())
    return {'message': 'Login realizado com sucesso', 'user': user_public(user),
            'token': issue_token(user), 'expires_in': current_app.config['TOKEN_MAX_AGE']}
