from pathlib import Path
import click
from database import db
from context import components
from services.errors import DomainError
from services.seeding import seed_demo
from utils.constants import MAX_ID


def register_commands(app):
    @app.cli.command('init-db')
    def init_db():
        """Cria tabelas ausentes sem apagar registros; não executa seed."""
        if db.engine.dialect.name == 'sqlite' and db.engine.url.database != ':memory:':
            Path(db.engine.url.database).parent.mkdir(parents=True, exist_ok=True)
        db.create_all()
        click.echo('Schema inicializado; registros existentes preservados.')

    @app.cli.command('create-admin')
    @click.option('--name', prompt=True)
    @click.option('--email', prompt=True)
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, password):
        """Cria administrador explicitamente, sem credenciais padrão."""
        try:
            user = components().accounts.create({'name': name, 'email': email, 'password': password,
                                                  'role': 'admin'}, privileged=True)
        except DomainError as error:
            raise click.ClickException(error.message) from None
        click.echo(f'Administrador criado: {user.id}')

    @app.cli.command('reset-password')
    @click.option('--user-id', required=True, type=click.IntRange(1, MAX_ID))
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def reset_password(user_id, password):
        """Redefine senha inclusive de conta MD5, preservando seus demais dados."""
        try:
            components().accounts.reset_password(user_id, password)
        except DomainError as error:
            raise click.ClickException(error.message) from None
        click.echo('Senha redefinida; tokens anteriores invalidados.')

    @app.cli.command('seed-demo')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def seed(password):
        """Insere demonstração atomicamente; recusa banco preenchido."""
        try:
            counts = seed_demo(db.session(), password)
        except DomainError as error:
            raise click.ClickException(error.message) from None
        click.echo(f'Seed concluído: {counts}')
