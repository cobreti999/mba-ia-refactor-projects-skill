from utils.clock import utc_now


def user_public(user):
    return {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role,
            'active': user.active, 'created_at': str(user.created_at)}


def task_public(task, overdue=False, relations=False, now=None):
    data = {key: getattr(task, key) for key in
            ('id', 'title', 'description', 'status', 'priority', 'user_id', 'category_id')}
    data.update(created_at=str(task.created_at), updated_at=str(task.updated_at),
                due_date=str(task.due_date) if task.due_date else None,
                tags=task.tags.split(',') if task.tags else [])
    if overdue:
        data['overdue'] = task.is_overdue(now or utc_now())
    if relations:
        data['user_name'] = task.user.name if task.user else None
        data['category_name'] = task.category.name if task.category else None
    return data


def task_for_user(task, now):
    data = task_public(task, overdue=True, now=now)
    return {key: data[key] for key in
            ('id', 'title', 'description', 'status', 'priority', 'created_at', 'due_date', 'overdue')}


def category_public(category):
    return {'id': category.id, 'name': category.name, 'description': category.description,
            'color': category.color, 'created_at': str(category.created_at)}
