from flask import g
from context import components
from http_support import body
from views.serializers import category_public


def summary():
    return components().reports.summary()


def user(user_id):
    return components().reports.user(user_id, g.actor)


def categories():
    return [{**category_public(category), 'task_count': total}
            for category, total in components().repository.categories_with_counts()]


def create_category():
    return category_public(components().categories.create(body())), 201


def update_category(cat_id):
    return category_public(components().categories.update(cat_id, body()))


def delete_category(cat_id):
    components().categories.delete(cat_id)
    return {'message': 'Categoria deletada'}
