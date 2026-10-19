from models import Category
from repositories.store import transaction
from services.validation import category_data, integer
from services.errors import DomainError


class CategoryService:
    def __init__(self, repository):
        self.repo, self.session = repository, repository.session

    def require(self, category_id):
        integer(category_id, 'ID')
        category = self.repo.get(Category, category_id)
        if category is None:
            raise DomainError('Categoria não encontrada', 404)
        return category

    def create(self, data):
        values = category_data(data, creating=True)
        values.setdefault('description', '')
        with transaction(self.session):
            category = self.repo.add(Category(**values))
        return category

    def update(self, category_id, data):
        values = category_data(data)
        with transaction(self.session):
            category = self.require(category_id)
            for key, value in values.items():
                setattr(category, key, value)
        return category

    def delete(self, category_id):
        with transaction(self.session):
            self.repo.delete_category(self.require(category_id))
