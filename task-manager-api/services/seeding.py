from datetime import timedelta
from models import User, Task, Category
from repositories.store import Repository, transaction
from services.errors import DomainError
from services.validation import password as validate_password
from utils.clock import utc_now


def seed_demo(session, password):
    validate_password(password)
    repo = Repository(session)
    with transaction(session):
        if any(repo.count(model) for model in (User, Task, Category)):
            raise DomainError('Seed exige banco vazio; os registros existentes foram preservados', 409)
        users = []
        for name, role in (('Demo Admin', 'admin'), ('Demo User', 'user'), ('Demo Manager', 'manager')):
            user = User(name=name, email=f'{role}@example.test', role=role)
            user.set_password(password)
            users.append(repo.add(user))
        categories = [repo.add(Category(name=name, description=f'Demo {name}', color=color))
                      for name, color in (('Backend', '#3498db'), ('Frontend', '#2ecc71'),
                                          ('DevOps', '#e74c3c'), ('Bug', '#e67e22'))]
        now = utc_now()
        fixtures = (
            ('Implementar autenticação', 'pending', 1, 0, 0, -3),
            ('Criar tela de login', 'in_progress', 2, 1, 1, 5),
            ('Configurar CI/CD', 'done', 2, 2, 2, None),
            ('Corrigir filtro de busca', 'pending', 1, 0, 3, -1),
            ('Adicionar paginação', 'pending', 3, 0, 0, 10),
            ('Escrever testes', 'pending', 2, 1, 0, None),
            ('Documentar API', 'cancelled', 4, 2, 0, None),
            ('Refatorar models', 'in_progress', 3, 1, 0, None),
            ('Configurar monitoramento', 'pending', 4, 2, 2, 20),
            ('Melhorar validações', 'pending', 3, 0, 0, None),
        )
        for title, status, priority, user, category, days in fixtures:
            repo.add(Task(title=title, description='Dado demonstrativo', status=status, priority=priority,
                          user_id=users[user].id, category_id=categories[category].id,
                          due_date=now + timedelta(days=days) if days is not None else None))
    return {'users': 3, 'categories': 4, 'tasks': 10}
