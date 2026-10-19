"""Conexões explícitas e unidades de trabalho SQLite."""
import sqlite3
from contextlib import contextmanager


def connect(path):
    connection = sqlite3.connect(path, isolation_level=None, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def transaction(connection):
    # Bloqueia concorrentes antes de consultar estoque e iniciar as gravações.
    connection.execute('BEGIN IMMEDIATE')
    try:
        yield
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def initialize(path):
    connection = connect(path)
    try:
        with transaction(connection):
            for statement in SCHEMA:
                connection.execute(statement)
            columns = {row['name'] for row in connection.execute('PRAGMA table_info(usuarios)')}
            if 'senha_format' not in columns:
                connection.execute("ALTER TABLE usuarios ADD COLUMN senha_format TEXT NOT NULL DEFAULT 'plaintext'")
    finally:
        connection.close()


SCHEMA = (
    '''CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, descricao TEXT,
        preco REAL, estoque INTEGER, categoria TEXT, ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
    '''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, senha TEXT,
        tipo TEXT DEFAULT 'cliente', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        senha_format TEXT NOT NULL DEFAULT 'plaintext')''',
    '''CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, status TEXT DEFAULT 'pendente',
        total REAL, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
    '''CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER,
        produto_id INTEGER, quantidade INTEGER, preco_unitario REAL)''',
)
