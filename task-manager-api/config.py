import os
from pathlib import Path


def load_config(overrides=None):
    path = os.environ.get('TASK_DATABASE', str(Path(__file__).resolve().parent / 'instance' / 'tasks.db'))
    config = {
        'SECRET_KEY': os.environ.get('TASK_SECRET_KEY'),
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(Path(path).resolve()),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'TOKEN_MAX_AGE': int(os.environ.get('TASK_TOKEN_MAX_AGE', '3600')),
        'CORS_ORIGINS': os.environ.get('TASK_CORS_ORIGINS', '*').split(','),
        'DEBUG': False,
    }
    config.update(overrides or {})
    if not isinstance(config['SECRET_KEY'], str) or len(config['SECRET_KEY']) < 32:
        raise RuntimeError('TASK_SECRET_KEY deve conter ao menos 32 caracteres')
    if type(config['TOKEN_MAX_AGE']) is not int or config['TOKEN_MAX_AGE'] <= 0:
        raise RuntimeError('TASK_TOKEN_MAX_AGE deve ser inteiro positivo')
    return config
