import os
from pathlib import Path


def load_config(overrides=None):
    config = {
        'SECRET_KEY': os.environ.get('APP_SECRET_KEY'),
        'DATABASE': os.environ.get('APP_DATABASE', str(Path(__file__).resolve().parents[1] / 'loja.db')),
        'TOKEN_MAX_AGE': int(os.environ.get('APP_TOKEN_MAX_AGE', '3600')),
        'ALLOW_DB_RESET': os.environ.get('APP_ALLOW_DB_RESET', 'false').lower() == 'true',
        'CORS_ORIGINS': os.environ.get('APP_CORS_ORIGINS', '*').split(','),
        'DEBUG': False,
        'MAX_CONTENT_LENGTH': 1024 * 1024,
    }
    config.update(overrides or {})
    if not isinstance(config['SECRET_KEY'], str) or len(config['SECRET_KEY']) < 32:
        raise RuntimeError('APP_SECRET_KEY deve conter pelo menos 32 caracteres')
    if type(config['TOKEN_MAX_AGE']) is not int or config['TOKEN_MAX_AGE'] <= 0:
        raise RuntimeError('APP_TOKEN_MAX_AGE deve ser um inteiro positivo')
    return config
