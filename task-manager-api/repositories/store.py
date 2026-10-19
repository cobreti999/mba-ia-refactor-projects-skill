from contextlib import contextmanager
from sqlalchemy import select, func, case, delete, update
from sqlalchemy.orm import joinedload
from models import User, Task, Category


@contextmanager
def transaction(session):
    # Leituras de autenticação já podem ter iniciado a transação da sessão.
    # A unidade de trabalho da requisição confirma todas as escritas juntas.
    try:
        yield
        session.commit()
    except BaseException:
        session.rollback()
        raise


class Repository:
    def __init__(self, session):
        self.session = session

    def get(self, model, entity_id):
        return self.session.get(model, entity_id)

    def by_email(self, email):
        return self.session.scalar(select(User).where(User.email == email))

    def add(self, entity):
        self.session.add(entity)
        self.session.flush()
        return entity

    def count(self, model):
        return self.session.scalar(select(func.count()).select_from(model))

    def tasks(self, filters=None, scope=None):
        query = select(Task).options(joinedload(Task.user), joinedload(Task.category))
        if scope is not None:
            query = query.where(Task.user_id == scope)
        for key, value in (filters or {}).items():
            if key == 'q':
                if value:
                    query = query.where(Task.title.like(f'%{value}%') | Task.description.like(f'%{value}%'))
            else:
                query = query.where(getattr(Task, key) == value)
        return list(self.session.scalars(query.order_by(Task.id)))

    def users_with_counts(self):
        return list(self.session.execute(select(User, func.count(Task.id),
                    func.coalesce(func.sum(case((Task.status == 'done', 1), else_=0)), 0))
                    .outerjoin(Task, Task.user_id == User.id).group_by(User.id).order_by(User.id)))

    def categories_with_counts(self):
        return list(self.session.execute(select(Category, func.count(Task.id))
                    .outerjoin(Task, Task.category_id == Category.id)
                    .group_by(Category.id).order_by(Category.id)))

    def delete_task(self, task):
        self.session.delete(task)

    def delete_user(self, user):
        self.session.execute(delete(Task).where(Task.user_id == user.id))
        self.session.delete(user)

    def delete_category(self, category):
        self.session.execute(update(Task).where(Task.category_id == category.id).values(category_id=None))
        self.session.delete(category)
