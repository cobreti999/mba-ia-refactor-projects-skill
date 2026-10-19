import click
from flask import current_app
from loja.context import components
from loja.database import initialize
from loja.errors import DomainError


def register_commands(app):
    @app.cli.command('init-db')
    def init_db():
        """Cria schema vazio ou adiciona marcador de senha sem apagar dados."""
        initialize(current_app.config['DATABASE'])
        click.echo('Schema inicializado; nenhum seed executado.')

    @app.cli.command('migrate-passwords')
    def migrate_passwords():
        """Converte somente senhas marcadas como plaintext. Faça backup antes."""
        try:
            count = components().accounts.migrate_passwords()
        except DomainError as error:
            raise click.ClickException(error.message) from None
        click.echo(f'Senhas migradas: {count}')

    @app.cli.command('create-admin')
    @click.option('--nome', prompt=True)
    @click.option('--email', prompt=True)
    @click.option('--senha', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(nome, email, senha):
        """Cria administrador explicitamente, sem credenciais embutidas."""
        try:
            user_id = components().accounts.register({'nome': nome, 'email': email, 'senha': senha}, role='admin')
        except DomainError as error:
            raise click.ClickException(error.message) from None
        click.echo(f'Administrador criado: {user_id}')
