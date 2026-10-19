from types import SimpleNamespace
from flask import g
from database import db
from repositories.store import Repository
from services.accounts import AccountService
from services.tasks import TaskService
from services.categories import CategoryService
from services.reports import ReportService


def components():
    if 'components' not in g:
        repo = Repository(db.session())
        g.components = SimpleNamespace(repository=repo, accounts=AccountService(repo),
                                       tasks=TaskService(repo), categories=CategoryService(repo),
                                       reports=ReportService(repo))
    return g.components
