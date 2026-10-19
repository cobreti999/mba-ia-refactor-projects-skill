from flask import g
from context import components
from http_support import body
from utils.clock import utc_now
from views.serializers import task_public


def listing():
    now = utc_now()
    return [task_public(task, overdue=True, relations=True, now=now)
            for task in components().tasks.list(g.actor)]


def detail(task_id):
    return task_public(components().tasks.require(task_id, g.actor), overdue=True)


def create():
    return task_public(components().tasks.create(body(), g.actor)), 201


def update(task_id):
    return task_public(components().tasks.update(task_id, body(), g.actor))


def delete(task_id):
    components().tasks.delete(task_id, g.actor)
    return {'message': 'Task deletada com sucesso'}


def search():
    from flask import request
    return [task_public(task) for task in components().tasks.list(g.actor, request.args)]


def stats():
    return components().reports.stats(g.actor)
