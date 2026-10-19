from collections import Counter
from datetime import timedelta
from models import User, Category
from services.errors import DomainError
from services.tasks import require_owner
from services.validation import integer
from utils.clock import utc_now
from utils.constants import VALID_STATUSES, TEAM_ROLES


def percentage(part, total):
    return round(part / total * 100, 2) if total else 0


def statistics(tasks, now):
    counts = Counter(task.status for task in tasks)
    return {'total': len(tasks), **{status: counts[status] for status in VALID_STATUSES},
            'overdue': sum(task.is_overdue(now) for task in tasks),
            'completion_rate': percentage(counts['done'], len(tasks))}


class ReportService:
    def __init__(self, repository):
        self.repo = repository

    def stats(self, actor):
        tasks = self.repo.tasks(scope=None if actor.role in TEAM_ROLES else actor.id)
        return statistics(tasks, utc_now())

    def summary(self):
        now = utc_now()
        tasks = self.repo.tasks()
        stats = statistics(tasks, now)
        priorities = Counter(task.priority for task in tasks)
        recent = now - timedelta(days=7)
        return {
            'generated_at': str(now),
            'overview': {'total_tasks': len(tasks), 'total_users': self.repo.count(User),
                         'total_categories': self.repo.count(Category)},
            'tasks_by_status': {status: stats[status] for status in VALID_STATUSES},
            'tasks_by_priority': dict(zip(('critical', 'high', 'medium', 'low', 'minimal'),
                                         (priorities[level] for level in range(1, 6)))),
            'overdue': {'count': stats['overdue'], 'tasks': [
                {'id': task.id, 'title': task.title, 'due_date': str(task.due_date),
                 'days_overdue': (now - task.due_date).days}
                for task in tasks if task.is_overdue(now)]},
            'recent_activity': {
                'tasks_created_last_7_days': sum(task.created_at >= recent for task in tasks),
                'tasks_completed_last_7_days': sum(task.status == 'done' and task.updated_at >= recent for task in tasks)},
            'user_productivity': [
                {'user_id': user.id, 'user_name': user.name, 'total_tasks': total,
                 'completed_tasks': completed, 'completion_rate': percentage(completed, total)}
                for user, total, completed in self.repo.users_with_counts()],
        }

    def user(self, user_id, actor):
        integer(user_id, 'ID')
        require_owner(actor, user_id)
        user = self.repo.get(User, user_id)
        if user is None:
            raise DomainError('Usuário não encontrado', 404)
        tasks = self.repo.tasks({'user_id': user_id})
        stats = statistics(tasks, utc_now())
        return {'user': {'id': user.id, 'name': user.name, 'email': user.email},
                'statistics': {'total_tasks': len(tasks),
                               **{key: stats[key] for key in (*VALID_STATUSES, 'overdue', 'completion_rate')},
                               'high_priority': sum(task.priority <= 2 for task in tasks)}}
