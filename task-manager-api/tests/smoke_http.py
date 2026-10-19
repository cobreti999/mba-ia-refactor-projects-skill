"""Boot real e contratos HTTP usando somente banco e credenciais descartáveis."""
import json
import os
from pathlib import Path
import platform
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from importlib.metadata import version

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from app import create_app
from database import db
from context import components

EVIDENCE = {'runtime': platform.python_version(),
            'dependencies': {p: version(p) for p in ('flask','flask-sqlalchemy','flask-cors','sqlalchemy','werkzeug','itsdangerous')},
            'isolation': 'temporary SQLite file, synthetic credentials and loopback port allocated by OS',
            'requests': [], 'passed': False}
SENSITIVE = []


def main():
    key, password = secrets.token_urlsafe(48), secrets.token_urlsafe(24)
    SENSITIVE.extend([key, password])
    tokens = {}
    with tempfile.TemporaryDirectory(prefix='task-manager-http-') as directory:
        database = Path(directory) / 'test.db'
        app = create_app({'SECRET_KEY': key, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(database)})
        adapter = app.url_map.bind('localhost')
        expected_routes = {(method, rule.rule) for rule in app.url_map.iter_rules()
                           for method in rule.methods - {'HEAD','OPTIONS'}}
        assert len(expected_routes) == 22
        with app.app_context():
            db.create_all()
            admin = components().accounts.create({'name':'HTTP Admin','email':'admin@example.test',
                                                  'password':password,'role':'admin'}, privileged=True)
            manager = components().accounts.create({'name':'HTTP Manager','email':'manager@example.test',
                                                    'password':password,'role':'manager'}, privileged=True)
            admin_id, manager_id = admin.id, manager.id
            db.session.remove(); db.engine.dispose()
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        env = {**os.environ, 'TASK_SECRET_KEY':key, 'TASK_DATABASE':str(database),
               'TASK_HOST':'127.0.0.1', 'TASK_PORT':str(port), 'PYTHONUNBUFFERED':'1'}
        log_path = Path(directory) / 'server.log'
        process = None
        boot = EVIDENCE['boot'] = {'command':'python app.py','host':'127.0.0.1','ready':False,'process_stopped':False}
        success = set()
        try:
            with log_path.open('w') as log:
                process = subprocess.Popen([sys.executable,'app.py'],cwd=PROJECT,env=env,stdout=log,stderr=subprocess.STDOUT)
            boot['pid'] = process.pid
            deadline = time.monotonic() + 60
            base = f'http://127.0.0.1:{port}'
            boot['port'] = port
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Server exited before readiness')
                try:
                    with urlopen(base+'/',timeout=.5) as response:
                        if response.status == 200:
                            boot['ready'] = True
                            break
                except (URLError,TimeoutError): pass
                time.sleep(.05)
            if not boot['ready']: raise TimeoutError('Server did not become ready')

            def call(name, method, path, expected=200, data=None, actor='admin', raw=None, extra_headers=None):
                headers = {'Content-Type':'application/json'}
                if actor and actor in tokens:
                    headers['Authorization'] = 'Bearer '+tokens[actor]
                headers.update(extra_headers or {})
                payload = raw.encode() if raw is not None else json.dumps(data).encode() if data is not None else None
                request = Request(base+path, data=payload, headers=headers, method=method)
                try:
                    response = urlopen(request,timeout=5)
                except HTTPError as error: response = error
                with response:
                    observed = response.code
                    result = json.loads(response.read())
                rule, _params = adapter.match(urlsplit(path).path, method=method, return_rule=True)
                record = {'name':name,'method':method,'path':rule.rule,'request_path':path,
                          'expected':expected,'observed':observed,
                          'keys':sorted(result) if isinstance(result,dict) else sorted(result[0]) if result else [],
                          'items':len(result) if isinstance(result,list) else None}
                EVIDENCE['requests'].append(record)
                assert observed == expected, f'{name}: expected {expected}, observed {observed}'
                if observed in (200,201): success.add((method,rule.rule))
                if isinstance(result,dict) and 'token' in result:
                    SENSITIVE.append(result['token'])
                assert '"password"' not in json.dumps(result), name+' exposed password'
                return result

            def snapshot(query, params=()):
                with sqlite3.connect(database) as connection:
                    return connection.execute(query,params).fetchall()

            root=call('root','GET','/',actor=None);assert root['message']=='Task Manager API'
            health=call('health','GET','/health',actor=None);assert set(health)=={'status','timestamp'}
            for name in ('admin','manager'):
                login=call(name+' login','POST','/login',data={'email':name+'@example.test','password':password},actor=None)
                tokens[name]=login['token'];assert login['expires_in']==3600
            alice=call('public registration','POST','/users',201,{'name':'HTTP Alice','email':'alice@example.test','password':password},actor=None)
            bob=call('second public registration','POST','/users',201,{'name':'HTTP Bob','email':'bob@example.test','password':password},actor=None)
            uid,bid=alice['id'],bob['id']
            for name in ('alice','bob'):
                tokens[name]=call(name+' login','POST','/login',data={'email':name+'@example.test','password':password},actor=None)['token']
            category=call('create category','POST','/categories',201,{'name':'HTTP Category','color':'#aabbcc'})
            cid=category['id'];assert category['description']==''
            categories=call('list categories','GET','/categories',actor='alice')
            assert categories[0]['task_count']==0
            updated=call('update category','PUT',f'/categories/{cid}',data={'description':'HTTP Updated'})
            assert updated['description']=='HTTP Updated'
            created=call('create owned task','POST','/tasks',201,{'title':'HTTP Task','category_id':cid,'priority':2,
                         'due_date':'2020-01-01','tags':['one','two']},actor='alice')
            tid=created['id'];assert created['user_id']==uid and created['description']==''
            assert created['tags']==['one','two'] and 'overdue' not in created
            listing=call('list owned tasks','GET','/tasks',actor='alice')
            assert len(listing)==1 and listing[0]['user_name']=='HTTP Alice' and listing[0]['overdue'] is True
            detail=call('task detail','GET',f'/tasks/{tid}',actor='alice');assert detail['overdue'] is True
            found=call('task search','GET',f'/tasks/search?q=HTTP&priority=2&user_id={uid}',actor='alice')
            assert [t['id'] for t in found]==[tid] and 'overdue' not in found[0]
            stats=call('task stats','GET','/tasks/stats',actor='alice');assert stats['total']==1 and stats['overdue']==1
            users=call('list users','GET','/users');assert len(users)==4
            user=call('own user detail','GET',f'/users/{uid}',actor='alice');assert user['tasks'][0]['id']==tid
            own=call('user task projection','GET',f'/users/{uid}/tasks',actor='alice')
            assert own[0]['overdue'] and 'user_id' not in own[0]
            summary=call('team summary','GET','/reports/summary',actor='manager')
            assert summary['overview']=={'total_tasks':1,'total_users':4,'total_categories':1}
            report=call('own report','GET',f'/reports/user/{uid}',actor='alice')
            assert report['statistics']['overdue']==1 and report['statistics']['high_priority']==1
            changed=call('update owned task','PUT',f'/tasks/{tid}',data={'status':'done'},actor='alice')
            assert changed['status']=='done'
            assert call('completed task is not overdue','GET',f'/tasks/{tid}',actor='alice')['overdue'] is False
            profile=call('update own profile','PUT',f'/users/{uid}',data={'name':'HTTP Alice Updated'},actor='alice')
            assert profile['name']=='HTTP Alice Updated'
            call('no authentication','GET','/users',401,actor=None)
            call('user cannot list team','GET','/users',403,actor='alice')
            call('user cannot read global report','GET','/reports/summary',403,actor='alice')
            call('tampered token','GET','/tasks',401,actor=None,extra_headers={'Authorization':'Bearer '+tokens['alice']+'invalid'})
            call('signup cannot grant admin','POST','/users',403,{'name':'Escalation','email':'escalate@example.test','password':password,'role':'admin'},actor=None)
            call('cross user task access','GET',f'/tasks/{tid}',403,actor='bob')
            call('own role cannot escalate','PUT',f'/users/{uid}',403,{'role':'admin'},actor='alice')
            call('cannot assign another owner','POST','/tasks',403,{'title':'Forbidden assignment','user_id':bid},actor='alice')
            call('manager cannot delete accounts','DELETE',f'/users/{bid}',403,actor='manager')
            call('invalid filter','GET','/tasks/search?priority=not-an-integer',400)
            call('invalid input type','POST','/tasks',400,{'title':123})
            call('malformed JSON','POST','/tasks',400,raw='{')
            call('deactivate user','PUT',f'/users/{bid}',data={'active':False})
            call('inactive identity invalidates token','GET','/tasks',401,actor='bob')
            call('delete category','DELETE',f'/categories/{cid}',actor='manager')
            assert snapshot('SELECT category_id FROM tasks WHERE id=?',(tid,))==[(None,)]
            assert snapshot('SELECT id FROM categories WHERE id=?',(cid,))==[]
            call('delete own task','DELETE',f'/tasks/{tid}',actor='alice')
            assert snapshot('SELECT id FROM tasks WHERE id=?',(tid,))==[]
            cascade=call('create task for cascade','POST','/tasks',201,{'title':'Cascade fixture','user_id':uid})
            call('admin removes user and owned tasks','DELETE',f'/users/{uid}')
            assert snapshot('SELECT id FROM users WHERE id=?',(uid,))==[]
            assert snapshot('SELECT id FROM tasks WHERE id=?',(cascade['id'],))==[]
            assert snapshot('SELECT COUNT(*) FROM users')==[(3,)]
            assert snapshot('PRAGMA foreign_key_check')==[]
            call('removed user token invalid','GET','/tasks',401,actor='alice')
            call('missing task','GET',f'/tasks/{tid}',404)
            assert success==expected_routes, 'Endpoint matrix incomplete'
            EVIDENCE.update(verified_endpoints=len(success),database_effects_verified=True,
                            effects={'category_delete_unlinks_task':True,'task_delete_persisted':True,
                                     'user_delete_removes_owned_tasks':True,'foreign_key_errors':0},passed=True)
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill();process.wait(timeout=5)
                boot.update(process_stopped=process.poll() is not None,exit_code=process.returncode)
            if log_path.exists():
                text=log_path.read_text(errors='replace')
                boot['server_log']=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',text)


if __name__=='__main__':
    try: main()
    except Exception as error:
        EVIDENCE['passed']=False
        EVIDENCE['failure']={'type':type(error).__name__}
        if isinstance(error,AssertionError):
            EVIDENCE['failure']['check']=str(error)
    raw=json.dumps(EVIDENCE)
    EVIDENCE['logs_contain_secrets']=any(secret in raw for secret in SENSITIVE)
    if EVIDENCE['logs_contain_secrets']: EVIDENCE['passed']=False
    safe=json.dumps(EVIDENCE,indent=2)
    for secret in SENSITIVE: safe=safe.replace(secret,'[REDACTED]')
    if len(sys.argv)>1: Path(sys.argv[1]).write_text(safe+'\n')
    print(json.dumps({'passed':EVIDENCE['passed'],'endpoints':EVIDENCE.get('verified_endpoints',0),
                      'cases':len(EVIDENCE['requests']),'process_stopped':EVIDENCE.get('boot',{}).get('process_stopped',False),
                      'logs_contain_secrets':EVIDENCE['logs_contain_secrets']}))
    raise SystemExit(0 if EVIDENCE['passed'] else 1)
