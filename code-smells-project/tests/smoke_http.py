"""Boot real e todos os 19 endpoints, usando apenas banco e identidades temporários."""
import importlib.metadata
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from loja import create_app
from loja.context import components
from loja.database import initialize


def run():
    evidence = []
    with tempfile.TemporaryDirectory(prefix='loja-smoke-') as folder:
        database = str(Path(folder) / 'smoke.db')
        secret = secrets.token_hex(32)
        password = secrets.token_urlsafe(24)
        initialize(database)
        app = create_app({'DATABASE': database, 'SECRET_KEY': secret})
        with app.app_context():
            admin_id = components().accounts.register({'nome':'Admin','email':'admin@example.test','senha':password}, 'admin')
        expected_routes = {(m, rule.rule) for rule in app.url_map.iter_rules() for m in rule.methods - {'HEAD','OPTIONS'}}
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        environment = dict(os.environ, APP_DATABASE=database, APP_SECRET_KEY=secret,
                           APP_HOST='127.0.0.1', APP_PORT=str(port), APP_ALLOW_DB_RESET='true')
        environment.pop('FLASK_DEBUG', None)
        base = f'http://127.0.0.1:{port}'
        with tempfile.TemporaryFile(mode='w+') as server_log:
            process = subprocess.Popen([sys.executable, 'app.py'], cwd=ROOT, env=environment,
                                       stdout=server_log, stderr=subprocess.STDOUT, text=True)
            def http(method, path, payload=None, token=None):
                headers = {'Content-Type':'application/json'}
                if token:
                    headers['Authorization'] = 'Bearer ' + token
                request = Request(base + path, data=None if payload is None else json.dumps(payload).encode(),
                                  headers=headers, method=method)
                try:
                    response = urlopen(request, timeout=5)
                except HTTPError as error:
                    response = error
                with response:
                    return response.status, json.load(response)
            def check(method, path, status, payload=None, token=None, route=None):
                actual, body = http(method, path, payload, token)
                assert actual == status, (method, path, status, actual, body)
                evidence.append({'method':method,'path':route or path.split('?')[0],
                                 'expected':status,'observed':actual,'keys':sorted(body)})
                return body
            def scalar(sql):
                connection = sqlite3.connect(database)
                try:
                    return connection.execute(sql).fetchone()[0]
                finally:
                    connection.close()
            try:
                deadline = time.monotonic() + 60
                while True:
                    assert process.poll() is None, 'Servidor encerrou antes da prontidão'
                    try:
                        status, result = http('GET', '/')
                        if status == 200 and result.get('versao') == '1.0.0':
                            break
                    except (URLError, ConnectionError, TimeoutError):
                        pass
                    if time.monotonic() > deadline:
                        raise AssertionError('Servidor não ficou pronto em 60 segundos')
                    time.sleep(.1)
                assert process.poll() is None
                check('GET','/',200)
                health = check('GET','/health',200)
                assert health['counts']['usuarios'] == 1 and 'secret_key' not in health
                admin = check('POST','/login',200,{'email':'admin@example.test','senha':password})['token']
                uid = check('POST','/usuarios',201,{'nome':'Cliente','email':'user@example.test','senha':password})['dados']['id']
                user = check('POST','/login',200,{'email':'user@example.test','senha':password})['token']
                product = {'nome':"Livro d'arte",'descricao':'Fixture','preco':25,'estoque':10,'categoria':'livros'}
                pid = check('POST','/produtos',201,product,admin)['dados']['id']
                assert scalar('SELECT estoque FROM produtos') == 10
                assert check('GET','/produtos',200)['dados'][0]['nome'] == product['nome']
                assert check('GET',"/produtos/busca?q=Livro",200)['total'] == 1
                assert check('GET',f'/produtos/{pid}',200,route='/produtos/<int:id>')['dados']['preco'] == 25
                check('PUT',f'/produtos/{pid}',200,product | {'preco':30},admin,route='/produtos/<int:id>')
                assert scalar('SELECT preco FROM produtos') == 30
                users = check('GET','/usuarios',200,token=admin)['dados']
                assert len(users) == 2 and all('senha' not in row for row in users)
                assert check('GET',f'/usuarios/{uid}',200,token=user,route='/usuarios/<int:id>')['dados']['id'] == uid
                created = check('POST','/pedidos',201,{'usuario_id':uid,'itens':[{'produto_id':pid,'quantidade':2}]},user)['dados']
                oid = created['pedido_id']
                assert created['total'] == 60 and scalar('SELECT estoque FROM produtos') == 8
                assert scalar('SELECT quantidade FROM itens_pedido') == 2
                assert len(check('GET','/pedidos',200,token=admin)['dados']) == 1
                listed = check('GET',f'/pedidos/usuario/{uid}',200,token=user,route='/pedidos/usuario/<int:usuario_id>')['dados']
                assert listed[0]['itens'][0]['produto_nome'] == product['nome']
                check('PUT',f'/pedidos/{oid}/status',200,{'status':'aprovado'},admin,route='/pedidos/<int:pedido_id>/status')
                assert scalar('SELECT status FROM pedidos') == 'aprovado'
                report = check('GET','/relatorios/vendas',200,token=admin)['dados']
                assert report['faturamento_bruto'] == 60 and report['pedidos_aprovados'] == 1
                assert check('POST','/admin/query',200,{'operacao':'contagens'},admin)['dados']['pedidos'] == 1
                # Acesso negado em rede real, além dos caminhos de sucesso acima.
                check('GET','/usuarios',401)
                check('GET','/usuarios',403,token=user)
                check('GET',f'/usuarios/{admin_id}',403,token=user,route='/usuarios/<int:id>')
                check('POST','/admin/query',400,{'sql':'SELECT * FROM usuarios'},admin)
                check('DELETE',f'/produtos/{pid}',200,token=admin,route='/produtos/<int:id>')
                assert scalar('SELECT COUNT(*) FROM produtos') == 0
                check('POST','/admin/reset-db',200,token=admin)
                for table in ('produtos','usuarios','pedidos','itens_pedido'):
                    assert scalar('SELECT COUNT(*) FROM ' + table) == 0
                assert { (r['method'],r['path']) for r in evidence if r['observed'] < 300 } == expected_routes
                assert len(expected_routes) == 19
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            server_log.seek(0)
            log = server_log.read()
        return {'python': sys.version.split()[0],
                'dependencies': {name:importlib.metadata.version(name) for name in ('flask','flask-cors','werkzeug','itsdangerous')},
                'boot': {'command':'python app.py','host':'127.0.0.1','port':port,'ready':True,'process_stopped':process.poll() is not None},
                'endpoints_verified':19,'requests':evidence,'database_effects_verified':True,'server_log':log}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
