import os
import secrets
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from itsdangerous import TimestampSigner
from werkzeug.security import check_password_hash
from loja import create_app
from loja.context import components
from loja.database import connect, initialize
from loja.errors import DomainError
from loja.http import signer
from loja.models.orders import OrderRepository
from loja.services.reports import discount_for


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'test.db')
        initialize(self.path)
        self.app = create_app({'DATABASE': self.path, 'SECRET_KEY': secrets.token_hex(32), 'TESTING': True})
        self.client = self.app.test_client()
        self.password = 'test-only-password'
        with self.app.app_context():
            ctx = components()
            self.admin_id = ctx.accounts.register({'nome': 'Admin', 'email': 'admin@example.test', 'senha': self.password}, 'admin')
            self.user_id = ctx.accounts.register({'nome': 'User', 'email': 'user@example.test', 'senha': self.password})
            self.other_id = ctx.accounts.register({'nome': 'Other', 'email': 'other@example.test', 'senha': self.password})
            self.product_id = ctx.products.create({'nome': "Livro d'arte", 'descricao': '', 'preco': 25, 'estoque': 10, 'categoria': 'livros'})
            self.admin = {'Authorization': 'Bearer ' + signer().dumps({'sub': self.admin_id})}
            self.user = {'Authorization': 'Bearer ' + signer().dumps({'sub': self.user_id})}

    def test_sql_values_and_safe_user_serialization(self):
        for email in ["' OR 1=1 --", 'admin@example.test']:
            response = self.client.post('/login', json={'email': email, 'senha': 'wrong'})
            self.assertEqual(response.status_code, 401)
        for query, count in [("d'arte", 1), ("' OR 1=1 --", 0)]:
            response = self.client.get('/produtos/busca', query_string={'q': query})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['total'], count)
        response = self.client.get('/usuarios', headers=self.admin)
        self.assertEqual(response.status_code, 200)
        for user in response.json['dados']:
            self.assertNotIn('senha', user)
            self.assertNotIn('senha_format', user)
        with self.app.app_context():
            user = components().users.get(self.user_id)
            self.assertNotEqual(user['senha'], self.password)
            self.assertTrue(check_password_hash(user['senha'], self.password))

    def test_auth_expiration_tampering_and_roles(self):
        self.assertEqual(self.client.get('/usuarios').status_code, 401)
        self.assertEqual(self.client.get('/usuarios', headers=self.user).status_code, 403)
        self.assertEqual(self.client.get(f'/usuarios/{self.other_id}', headers=self.user).status_code, 403)
        self.assertEqual(self.client.get(f'/usuarios/{self.user_id}', headers=self.user).status_code, 200)
        self.assertEqual(self.client.get('/usuarios', headers={'Authorization': self.admin['Authorization'] + 'tampered'}).status_code, 401)
        with self.app.app_context():
            with patch.object(TimestampSigner, 'get_timestamp', return_value=1):
                expired = signer().dumps({'sub': self.admin_id})
        self.assertEqual(self.client.get('/usuarios', headers={'Authorization': 'Bearer ' + expired}).status_code, 401)
        response = self.client.post('/usuarios', json={'nome': 'New', 'email': 'new@example.test', 'senha': self.password, 'tipo': 'admin'})
        self.assertEqual(response.status_code, 201)
        with self.app.app_context():
            self.assertEqual(components().users.get(response.json['dados']['id'])['tipo'], 'cliente')

    def test_admin_tools_are_restricted_and_reset_is_opt_in(self):
        self.assertEqual(self.client.post('/admin/reset-db', headers=self.admin).status_code, 403)
        self.assertEqual(self.client.post('/admin/query', headers=self.admin, json={'sql': 'DELETE FROM usuarios'}).status_code, 400)
        response = self.client.post('/admin/query', headers=self.admin, json={'operacao': 'contagens'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['dados']['usuarios'], 3)
        self.assertEqual(self.client.post('/admin/query', headers=self.user, json={'operacao': 'contagens'}).status_code, 403)

    def test_product_validation_and_serialization(self):
        valid = {'nome': 'Valid', 'preco': 0, 'estoque': 0, 'categoria': 'geral'}
        for change in [{'nome': 'x'}, {'nome': 5}, {'preco': True}, {'preco': -1}, {'preco': float('nan')},
                       {'preco': float('inf')}, {'estoque': 1.5}, {'estoque': True}, {'categoria': 'unknown'}]:
            for method, url in [('POST', '/produtos'), ('PUT', f'/produtos/{self.product_id}')]:
                response = self.client.open(url, method=method, headers=self.admin, json=valid | change)
                self.assertEqual(response.status_code, 400, (method, change))
        result = self.client.post('/produtos', headers=self.admin, json=valid)
        self.assertEqual(result.status_code, 201)
        product_id = result.json['dados']['id']
        single = self.client.get(f'/produtos/{product_id}').json['dados']
        listed = next(p for p in self.client.get('/produtos').json['dados'] if p['id'] == product_id)
        found = self.client.get('/produtos/busca?q=Valid&preco_max=0').json['dados'][0]
        self.assertEqual(single, listed)
        self.assertEqual(single, found)
        for query in ['preco_min=no', 'preco_max=nan', 'preco_min=5&preco_max=1']:
            self.assertEqual(self.client.get('/produtos/busca?' + query).status_code, 400)

    def test_orders_validate_quantity_owner_and_combined_stock(self):
        for quantity in [0, -1, 1.5, True, '1', 11]:
            response = self.client.post('/pedidos', headers=self.user, json={'usuario_id': self.user_id,
                'itens': [{'produto_id': self.product_id, 'quantidade': quantity}]})
            self.assertEqual(response.status_code, 400, quantity)
        response = self.client.post('/pedidos', headers=self.user, json={'usuario_id': self.other_id,
            'itens': [{'produto_id': self.product_id, 'quantidade': 1}]})
        self.assertEqual(response.status_code, 403)
        for quantities, expected in [([6, 6], 400), ([2, 3], 201)]:
            response = self.client.post('/pedidos', headers=self.user, json={'usuario_id': self.user_id,
                'itens': [{'produto_id': self.product_id, 'quantidade': q} for q in quantities]})
            self.assertEqual(response.status_code, expected)
        self.assertEqual(response.json['dados']['total'], 125)
        self.assertEqual(self.client.get(f'/produtos/{self.product_id}').json['dados']['estoque'], 5)
        order = self.client.get(f'/pedidos/usuario/{self.user_id}', headers=self.user).json['dados'][0]
        self.assertEqual(len(order['itens']), 1)
        self.assertEqual(order['itens'][0]['quantidade'], 5)

    def test_rollback_even_after_stock_write(self):
        with patch.object(OrderRepository, 'add_item', side_effect=RuntimeError('sensitive failure')):
            response = self.client.post('/pedidos', headers=self.user, json={'usuario_id': self.user_id,
                'itens': [{'produto_id': self.product_id, 'quantidade': 2}]})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('sensitive', response.get_data(as_text=True))
        with self.app.app_context():
            ctx = components()
            self.assertEqual(ctx.products.get(self.product_id)['estoque'], 10)
            self.assertEqual(ctx.admin.counts()['pedidos'], 0)
            self.assertEqual(ctx.connection.execute('SELECT COUNT(*) FROM itens_pedido').fetchone()[0], 0)
            ctx.checkout.create(self.user_id, [{'produto_id': self.product_id, 'quantidade': 1}])
            self.assertEqual(ctx.admin.counts()['pedidos'], 1)

    def test_concurrent_checkout_cannot_oversell(self):
        def checkout():
            with self.app.app_context():
                try:
                    components().checkout.create(self.user_id, [{'produto_id': self.product_id, 'quantidade': 7}])
                    return 'ok'
                except DomainError:
                    return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: checkout(), range(2)))
        self.assertCountEqual(results, ['ok', 'rejected'])
        with self.app.app_context():
            self.assertEqual(components().products.get(self.product_id)['estoque'], 3)
            self.assertEqual(components().admin.counts()['pedidos'], 1)

    def test_query_count_is_constant_and_missing_product_preserved(self):
        with self.app.app_context():
            ctx = components()
            ctx.checkout.create(self.user_id, [{'produto_id': self.product_id, 'quantidade': 1}])
            traces = []
            ctx.connection.set_trace_callback(traces.append)
            first = ctx.orders.list_with_items()
            self.assertEqual(len(traces), 2)
            ctx.connection.set_trace_callback(None)
            for _ in range(4):
                ctx.checkout.create(self.user_id, [{'produto_id': self.product_id, 'quantidade': 1}])
            ctx.products.delete(self.product_id)
            traces.clear()
            ctx.connection.set_trace_callback(traces.append)
            rows = ctx.orders.list_with_items()
            self.assertEqual(len(rows), 5)
            self.assertEqual(len(traces), 2)
            self.assertEqual(first[0][1][0]['quantidade'], rows[0][1][0]['quantidade'])
        response = self.client.get('/pedidos', headers=self.admin)
        self.assertEqual(response.json['dados'][0]['itens'][0]['produto_nome'], 'Desconhecido')

    def test_request_context_closes_connection_and_import_has_no_database_effect(self):
        with self.app.app_context():
            old = components().connection
        with self.assertRaises(sqlite3.ProgrammingError):
            old.execute('SELECT 1')
        with self.app.app_context():
            self.assertIsNot(components().connection, old)
        missing = str(Path(self.temp.name) / 'missing.db')
        create_app({'DATABASE': missing, 'SECRET_KEY': secrets.token_hex(32)})
        self.assertFalse(Path(missing).exists())
        with patch.dict(os.environ, {'APP_SECRET_KEY': ''}):
            with self.assertRaises(RuntimeError):
                create_app()

    def test_errors_and_health_do_not_expose_internal_details(self):
        health = self.client.get('/health')
        self.assertEqual(set(health.json), {'status', 'database', 'counts', 'versao'})
        for kwargs in [{'json': []}, {'json': 'text'}, {'data': '{', 'content_type': 'application/json'}, {'data': 'plain'}]:
            self.assertEqual(self.client.post('/usuarios', **kwargs).status_code, 400)
        self.assertEqual(self.client.get('/missing').status_code, 404)
        self.assertEqual(self.client.delete('/health').status_code, 405)
        self.assertEqual(self.client.put('/pedidos/999/status', headers=self.admin, json={'status': 'aprovado'}).status_code, 404)

    def test_discount_boundaries(self):
        for value, rate in [(999,0), (1000,0), (1001,.02), (5000,.02), (5001,.05), (10000,.05), (10001,.1)]:
            self.assertAlmostEqual(discount_for(value), value * rate)


class MigrationTests(unittest.TestCase):
    def test_legacy_migration_is_explicit_idempotent_and_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'legacy.db')
            connection = connect(path)
            connection.execute('''CREATE TABLE usuarios(id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT, email TEXT, senha TEXT, tipo TEXT, criado_em TEXT)''')
            # Prefixos que parecem hash não devem ser confundidos com formato já migrado.
            connection.execute('INSERT INTO usuarios VALUES (1,?,?,?,?,?)', ('Legacy','legacy@example.test','scrypt:literal-password','cliente','date'))
            connection.close()
            app = create_app({'DATABASE': path, 'SECRET_KEY': secrets.token_hex(32), 'TESTING': True})
            runner = app.test_cli_runner()
            self.assertEqual(runner.invoke(args=['init-db']).exit_code, 0)
            with app.app_context():
                self.assertEqual(components().users.get(1)['senha'], 'scrypt:literal-password')
            login = {'email': 'legacy@example.test', 'senha': 'scrypt:literal-password'}
            self.assertEqual(app.test_client().post('/login', json=login).status_code, 401)
            result = runner.invoke(args=['migrate-passwords'])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn('Senhas migradas: 1', result.output)
            self.assertEqual(app.test_client().post('/login', json=login).status_code, 200)
            self.assertIn('Senhas migradas: 0', runner.invoke(args=['migrate-passwords']).output)
            with app.app_context():
                ctx = components()
                ctx.connection.execute("INSERT INTO usuarios(nome,email,senha) VALUES ('Good','a','literal'),('Bad','b',NULL)")
                with self.assertRaises(DomainError):
                    ctx.accounts.migrate_passwords()
                self.assertEqual(ctx.users.by_email('a')['senha'], 'literal')
                self.assertEqual(ctx.users.get(1)['criado_em'], 'date')


if __name__ == '__main__':
    unittest.main()
