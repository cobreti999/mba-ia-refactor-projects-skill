"""Entrada compatível para seed explícito e não destrutivo."""
from getpass import getpass
from app import create_app
from database import db
from services.errors import DomainError
from services.seeding import seed_demo


def seed_data():
    app = create_app()
    password = getpass('Senha dos usuários demonstrativos: ')
    if password != getpass('Confirme a senha: '):
        raise SystemExit('As senhas não conferem')
    with app.app_context():
        try:
            counts = seed_demo(db.session(), password)
        except DomainError as error:
            raise SystemExit(error.message) from None
        print(f'Seed concluído: {counts}')


if __name__ == '__main__':
    seed_data()
