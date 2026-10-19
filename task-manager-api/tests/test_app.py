import hashlib
import logging
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy import event, select, func
from app import create_app
from database import db
from models import User, Task, Category
from http_support import issue_token
from repositories.store import Repository
from services.seeding import seed_demo
from utils.clock import utc_now


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.db'
        self.app = create_app({'SECRET_KEY': secrets.token_urlsafe(48),
                               'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(self.path), 'TESTING': True})
        self.client = self.app.test_client()
        self.password = secrets.token_urlsafe(18)
        self.ids, self.tokens = {}, {}
        with self.app.app_context():
            db.create_all()
            for name, role in (('admin', 'admin'), ('manager', 'manager'), ('alice', 'user'), ('bob', 'user')):
                user = User(name=name, email=f'{name}@example.test', role=role)
                user.set_password(self.password)
                db.session.add(user)
                db.session.flush()
                self.ids[name] = user.id
                self.tokens[name] = issue_token(user)
            category = Category(name='Backend')
            empty = Category(name='Empty')
            db.session.add_all([category, empty]); db.session.flush()
            self.category_id, self.empty_id = category.id, empty.id
            task = Task(title='Alice overdue', user_id=self.ids['alice'], category_id=category.id,
                        due_date=utc_now()-timedelta(days=2), tags='one,two', priority=1)
            other = Task(title='Bob completed', user_id=self.ids['bob'], status='done', priority=2)
            unassigned = Task(title='Unassigned task')
            db.session.add_all([task, other, unassigned]); db.session.flush()
            self.task_id, self.other_id = task.id, other.id
            db.session.commit()
        self.addCleanup(self.dispose)

    def dispose(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def request(self, method, path, data=None, actor='admin', **kwargs):
        headers = kwargs.pop('headers', {})
        if actor:
            headers['Authorization'] = 'Bearer ' + self.tokens[actor]
        return self.client.open(path, method=method, json=data, headers=headers, **kwargs)

    def count(self, model):
        with self.app.app_context():
            return db.session.scalar(select(func.count()).select_from(model))

    def test_password_hashes_and_all_user_representations_are_public(self):
        with self.app.app_context():
            alice = db.session.get(User, self.ids['alice'])
            bob = db.session.get(User, self.ids['bob'])
            self.assertNotEqual(alice.password, bob.password)
            self.assertTrue(alice.password.startswith('scrypt:'))
            self.assertTrue(alice.check_password(self.password))
            self.assertFalse(alice.check_password('incorrect'))
            stored = alice.password
        paths = ['/users', f"/users/{self.ids['alice']}"]
        for path in paths:
            response = self.request('GET', path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(stored, response.text)
            self.assertNotIn('"password"', response.text)
        created = self.request('POST', '/users', {'name': 'New User', 'email': 'new@example.test', 'password': self.password}, actor=None)
        self.assertEqual(created.status_code, 201)
        self.assertNotIn('password', created.json)
        login = self.request('POST', '/login', {'email': 'alice@example.test', 'password': self.password}, actor=None)
        self.assertEqual(login.status_code, 200)
        self.assertIn('token', login.json)
        self.assertNotIn('password', login.json['user'])
        self.assertEqual(self.request('POST', '/login', {'email': "' OR 1=1 --", 'password': self.password}, actor=None).status_code, 400)
        self.assertEqual(self.request('POST', '/login', {'email': 'alice@example.test', 'password': 'wrong'}, actor=None).status_code, 401)

    def test_real_tokens_expiration_tampering_and_current_account_state(self):
        self.assertEqual(self.request('GET', '/tasks', actor=None).status_code, 401)
        for token in ('fake-jwt-token-1', self.tokens['alice'] + 'tampered'):
            r = self.request('GET', '/tasks', actor=None, headers={'Authorization': 'Bearer ' + token})
            self.assertEqual(r.status_code, 401)
        with self.app.app_context(), patch('itsdangerous.timed.TimestampSigner.get_timestamp', return_value=int(time.time())-4000):
            expired = issue_token(db.session.get(User, self.ids['alice']))
        self.assertEqual(self.request('GET', '/tasks', actor=None, headers={'Authorization':'Bearer '+expired}).status_code, 401)
        response = self.request('PUT', f"/users/{self.ids['alice']}", {'active': False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.request('GET', '/tasks', actor='alice').status_code, 401)
        self.assertEqual(self.request('POST', '/login', {'email':'alice@example.test','password':self.password}, actor=None).status_code, 403)

    def test_roles_registration_privilege_escalation_and_manager_permissions(self):
        payload = {'name':'Escalation','email':'escalation@example.test','password':self.password,'role':'admin'}
        self.assertEqual(self.request('POST', '/users', payload, actor=None).status_code, 403)
        self.assertEqual(self.request('POST', '/users', payload, actor='manager').status_code, 403)
        self.assertEqual(self.request('POST', '/users', payload).status_code, 201)
        for data in ({'role':'admin'}, {'active':False}):
            self.assertEqual(self.request('PUT', f"/users/{self.ids['alice']}", data, actor='alice').status_code, 403)
        self.assertEqual(self.request('DELETE', f"/users/{self.ids['bob']}", actor='manager').status_code, 403)
        self.assertEqual(self.request('GET','/users',actor='alice').status_code,403)
        self.assertEqual(self.request('GET','/reports/summary',actor='alice').status_code,403)
        self.assertEqual(self.request('GET','/reports/summary',actor='manager').status_code,200)
        self.assertEqual(self.request('POST','/categories',{'name':'Manager category'},actor='manager').status_code,201)
        self.assertEqual(self.request('POST','/categories',{'name':'Forbidden'},actor='alice').status_code,403)
        # Roles are reloaded from the DB, not trusted from a token claim.
        self.assertEqual(self.request('PUT',f"/users/{self.ids['alice']}",{'role':'manager'}).status_code,200)
        self.assertEqual(self.request('GET','/reports/summary',actor='alice').status_code,200)

    def test_owner_scoping_and_reassignment_protection(self):
        tasks = self.request('GET','/tasks',actor='alice').json
        self.assertEqual([t['id'] for t in tasks],[self.task_id])
        self.assertEqual(self.request('GET','/tasks/stats',actor='alice').json['total'],1)
        self.assertEqual(self.request('GET','/tasks/stats',actor='manager').json['total'],3)
        for method, path, data in (
            ('GET',f'/tasks/{self.other_id}',None),('PUT',f'/tasks/{self.other_id}',{'title':'Stolen'}),
            ('DELETE',f'/tasks/{self.other_id}',None),('GET',f"/users/{self.ids['bob']}",None),
            ('GET',f"/users/{self.ids['bob']}/tasks",None),('GET',f"/reports/user/{self.ids['bob']}",None),
            ('GET',f"/tasks/search?user_id={self.ids['bob']}",None),
            ('POST','/tasks',{'title':'Invalid owner','user_id':self.ids['bob']}),
            ('PUT',f'/tasks/{self.task_id}',{'user_id':None}),
        ):
            with self.subTest(path=path,method=method):
                self.assertEqual(self.request(method,path,data,actor='alice').status_code,403)
        created=self.request('POST','/tasks',{'title':'Own task'},actor='alice')
        self.assertEqual(created.status_code,201)
        self.assertEqual(created.json['user_id'],self.ids['alice'])
        self.assertEqual(created.json['description'],'')
        self.assertEqual(self.request('PUT',f'/tasks/{self.other_id}',{'user_id':self.ids['alice']},actor='manager').status_code,200)

    def test_task_validation_post_put_boundaries_and_no_partial_update(self):
        bad = ({'title':12},{'title':'ab'},{'title':'x'*201},{'priority':True},{'priority':1.5},
               {'priority':'2'},{'priority':0},{'priority':6},{'status':[]},
               {'tags':['one',2]},{'tags':False},{'tags':'a'*501},{'description':{}},
               {'user_id':False},{'user_id':-1},{'category_id':0},{'due_date':12},{'due_date':'not-a-date'})
        for values in bad:
            for method,path in (('POST','/tasks'),('PUT',f'/tasks/{self.task_id}')):
                data={'title':'Valid title',**values}
                with self.subTest(data=values,method=method):
                    self.assertEqual(self.request(method,path,data).status_code,400)
        for length in (3,200):
            self.assertEqual(self.request('POST','/tasks',{'title':'a'*length,'priority':5}).status_code,201)
        r=self.request('GET',f'/tasks/{self.task_id}')
        self.assertEqual(r.json['title'],'Alice overdue')
        self.assertEqual(self.request('POST','/tasks',{'title':'Missing user','user_id':999}).status_code,404)
        self.assertEqual(self.request('POST','/tasks',{'title':'Missing category','category_id':999}).status_code,404)
        for query in ('priority=abc','user_id=abc','priority=0','priority=6','status=unknown',f'user_id={2**65}'):
            self.assertEqual(self.request('GET','/tasks/search?'+query).status_code,400)
        self.assertEqual(self.request('GET',f'/tasks/{2**65}').status_code,400)
        self.assertEqual(self.request('GET',"/tasks/search?q=%27%20OR%201%3D1%20--").json,[])

    def test_user_and_category_validation_and_conflict(self):
        for data in ({'name':[]},{'email':None},{'password':123},{'name':'x'*101},{'active':'false'}):
            self.assertEqual(self.request('PUT',f"/users/{self.ids['alice']}",data).status_code,400)
        self.assertEqual(self.request('PUT',f"/users/{self.ids['alice']}",{'email':'bob@example.test'}).status_code,409)
        duplicate={'name':'Duplicate','email':'alice@example.test','password':self.password}
        self.assertEqual(self.request('POST','/users',duplicate,actor=None).status_code,409)
        for data in ({'name':None},{'name':'x'*101},{'color':'#zzzzzz'},{'description':3}):
            self.assertEqual(self.request('POST','/categories',data).status_code,400)
            self.assertEqual(self.request('PUT',f'/categories/{self.category_id}',data).status_code,400)
        self.assertEqual(self.request('PUT','/categories/999',{'name':'Missing'}).status_code,404)
        for length, expected in ((3,400),(4,201),(128,201),(129,400)):
            response=self.request('POST','/users',{'name':'Boundary','email':f'length{length}@example.test',
                                                  'password':'a'*length},actor=None)
            self.assertEqual(response.status_code,expected)
        result=self.app.test_cli_runner().invoke(args=['create-admin'],
                    input='CLI Admin\ncli@example.test\n'+self.password+'\n'+self.password+'\n')
        self.assertEqual(result.exit_code,0)
        self.assertNotIn(self.password,result.output)

    def test_error_boundary_json_http_headers_and_sensitive_diagnostics(self):
        headers={'Authorization':'Bearer '+self.tokens['admin']}
        for raw,ctype in (('{','application/json'),('[]','application/json'),('null','application/json'),('x','text/plain')):
            response=self.client.post('/tasks',data=raw,content_type=ctype,headers=headers)
            self.assertEqual(response.status_code,400)
            self.assertTrue(response.is_json)
        missing=self.request('GET','/missing',actor=None)
        self.assertEqual(missing.status_code,404); self.assertTrue(missing.is_json)
        wrong=self.request('POST','/',{},actor=None)
        self.assertEqual(wrong.status_code,405); self.assertIn('GET',wrong.headers['Allow'])
        health=self.request('GET','/health',actor=None)
        self.assertEqual(set(health.json),{'status','timestamp'})
        secret='sensitive-diagnostic-must-not-appear'
        with patch.object(Repository,'tasks',side_effect=RuntimeError(secret)):
            with self.assertLogs(self.app.logger,level=logging.ERROR) as logs:
                response=self.request('GET','/tasks')
            self.assertEqual(response.status_code,500)
            self.assertNotIn(secret,response.text+' '.join(logs.output))
            self.assertIn('reference',response.json)
        self.assertEqual(self.request('GET','/tasks').status_code,200)

    def test_rollbacks_after_flushed_write_and_following_operation(self):
        original=Repository.add
        def fail(repo,entity):
            original(repo,entity)
            raise RuntimeError('synthetic-write-failure')
        before=self.count(Task)
        with patch.object(Repository,'add',fail), self.assertLogs(self.app.logger,level=logging.ERROR):
            self.assertEqual(self.request('POST','/tasks',{'title':'Must rollback'}).status_code,500)
        self.assertEqual(self.count(Task),before)
        self.assertEqual(self.request('POST','/tasks',{'title':'Next operation'}).status_code,201)
        self.assertEqual(self.count(Task),before+1)

    def test_category_delete_and_user_delete_are_atomic_with_expected_effects(self):
        original=Repository.delete_category
        def fail(repo,category):
            original(repo,category)
            repo.session.flush()
            raise RuntimeError('after-delete')
        with patch.object(Repository,'delete_category',fail), self.assertLogs(self.app.logger,level=logging.ERROR):
            self.assertEqual(self.request('DELETE',f'/categories/{self.category_id}').status_code,500)
        with self.app.app_context():
            self.assertEqual(db.session.get(Task,self.task_id).category_id,self.category_id)
            self.assertIsNotNone(db.session.get(Category,self.category_id))
        self.assertEqual(self.request('DELETE',f'/categories/{self.category_id}').status_code,200)
        with self.app.app_context():
            self.assertIsNone(db.session.get(Task,self.task_id).category_id)
        delete_user=Repository.delete_user
        def fail_user(repo,user):
            delete_user(repo,user); repo.session.flush(); raise RuntimeError('after-user-delete')
        with patch.object(Repository,'delete_user',fail_user), self.assertLogs(self.app.logger,level=logging.ERROR):
            self.assertEqual(self.request('DELETE',f"/users/{self.ids['alice']}").status_code,500)
        self.assertEqual(self.count(Task),3)
        self.assertEqual(self.request('DELETE',f"/users/{self.ids['alice']}").status_code,200)
        with self.app.app_context():
            self.assertIsNone(db.session.get(User,self.ids['alice']))
            self.assertIsNone(db.session.get(Task,self.task_id))
            self.assertIsNotNone(db.session.get(Task,self.other_id))
        self.assertEqual(self.request('DELETE',f"/users/{self.ids['alice']}").status_code,404)

    def test_n_plus_one_query_counts_do_not_grow_with_cardinality(self):
        with self.app.app_context(): engine=db.engine
        queries=[]
        def capture(_conn,_cursor,statement,_params,_context,_many):
            if statement.lstrip().upper().startswith('SELECT'):
                queries.append(statement)
        event.listen(engine,'before_cursor_execute',capture)
        self.addCleanup(event.remove,engine,'before_cursor_execute',capture)
        def counts():
            result={}
            for path in ('/tasks','/users','/categories','/reports/summary'):
                queries.clear(); response=self.request('GET',path)
                self.assertEqual(response.status_code,200)
                result[path]=len(queries)
            return result
        before=counts()
        with self.app.app_context():
            stored=db.session.get(User,self.ids['alice']).password
            for index in range(25):
                user=User(name=f'Bulk {index}',email=f'bulk{index}@example.test',password=stored)
                category=Category(name=f'Bulk {index}')
                db.session.add_all([user,category]);db.session.flush()
                db.session.add(Task(title=f'Bulk task {index}',user_id=user.id,category_id=category.id))
            db.session.commit()
        after=counts()
        self.assertEqual(before,after)
        self.assertEqual(after,{'/tasks':2,'/users':2,'/categories':2,'/reports/summary':5})
        cats=self.request('GET','/categories').json
        self.assertEqual(next(x['task_count'] for x in cats if x['id']==self.empty_id),0)
        self.assertEqual(self.request('GET','/reports/summary').json['overview']['total_tasks'],28)

    def test_overdue_and_statistics_share_clock_and_preserve_payload_variants(self):
        now=datetime(2026,10,19,12)
        task=Task(title='Boundary',due_date=now,status='pending')
        self.assertFalse(task.is_overdue(now))
        task.due_date=now-timedelta(microseconds=1)
        self.assertTrue(task.is_overdue(now))
        for status in ('done','cancelled'):
            task.status=status; self.assertFalse(task.is_overdue(now))
        task.due_date=None; self.assertFalse(task.is_overdue(now))
        listing=self.request('GET','/tasks',actor='alice').json[0]
        detail=self.request('GET',f'/tasks/{self.task_id}',actor='alice').json
        own=self.request('GET',f"/users/{self.ids['alice']}/tasks",actor='alice').json[0]
        summary=self.request('GET','/reports/summary').json
        stats=self.request('GET','/tasks/stats',actor='alice').json
        self.assertTrue(listing['overdue'] and detail['overdue'] and own['overdue'])
        self.assertEqual(summary['overdue']['count'],1); self.assertEqual(stats['overdue'],1)
        self.assertEqual(summary['tasks_by_status']['done'],1)
        self.assertEqual(summary['user_productivity'][2]['completion_rate'],0)
        self.assertIn('user_name',listing);self.assertNotIn('user_name',detail)
        self.assertNotIn('user_id',own);self.assertEqual(detail['tags'],['one','two'])
        self.assertEqual(self.request('GET',f"/reports/user/{self.ids['bob']}").json['statistics']['completion_rate'],100)

    def test_explicit_legacy_password_reset_preserves_records_and_revokes_tokens(self):
        with self.app.app_context():
            user=db.session.get(User,self.ids['alice'])
            original=(user.id,user.name,user.email,user.role,user.active,user.created_at)
            user.password=hashlib.md5(self.password.encode()).hexdigest()
            db.session.commit()
        self.assertEqual(self.request('POST','/login',{'email':'alice@example.test','password':self.password},actor=None).status_code,401)
        runner=self.app.test_cli_runner()
        result=runner.invoke(args=['init-db']);self.assertEqual(result.exit_code,0)
        result=runner.invoke(args=['reset-password','--user-id',str(self.ids['alice'])],input=self.password+'\n'+self.password+'\n')
        self.assertEqual(result.exit_code,0)
        self.assertNotIn(self.password,result.output)
        with self.app.app_context():
            user=db.session.get(User,self.ids['alice'])
            self.assertEqual((user.id,user.name,user.email,user.role,user.active,user.created_at),original)
            self.assertTrue(user.check_password(self.password))
            self.assertEqual(db.session.get(Task,self.task_id).user_id,user.id)
        self.assertEqual(self.request('GET','/tasks',actor='alice').status_code,401)
        login=self.request('POST','/login',{'email':'alice@example.test','password':self.password},actor=None)
        self.assertEqual(login.status_code,200)
        self.assertEqual(self.request('GET','/tasks',actor=None,headers={'Authorization':'Bearer '+login.json['token']}).status_code,200)

    def test_password_update_revokes_previous_token(self):
        response=self.request('PUT',f"/users/{self.ids['alice']}",{'password':'replacement-fixture-password'},actor='alice')
        self.assertEqual(response.status_code,200);self.assertNotIn('password',response.json)
        self.assertEqual(self.request('GET','/tasks',actor='alice').status_code,401)

    def test_seed_refuses_existing_data_and_rolls_back_each_stage(self):
        runner=self.app.test_cli_runner()
        result=runner.invoke(args=['seed-demo'],input=self.password+'\n'+self.password+'\n')
        self.assertNotEqual(result.exit_code,0)
        self.assertEqual(self.count(Task),3);self.assertEqual(self.count(User),4)
        with self.app.app_context():
            db.drop_all();db.create_all()
            for model in (User,Category,Task):
                original=Repository.add
                def fail(repo,entity,model=model):
                    result=original(repo,entity)
                    if isinstance(entity,model): raise RuntimeError('synthetic-seed-failure')
                    return result
                with patch.object(Repository,'add',fail),self.assertRaises(RuntimeError):
                    seed_demo(db.session(),self.password)
                for table in (User,Category,Task):
                    self.assertEqual(db.session.scalar(select(func.count()).select_from(table)),0)
            counts=seed_demo(db.session(),self.password)
            self.assertEqual(counts,{'users':3,'categories':4,'tasks':10})
        result=runner.invoke(args=['seed-demo'],input=self.password+'\n'+self.password+'\n')
        self.assertNotEqual(result.exit_code,0)
        self.assertEqual(self.count(Task),10)

    def test_concurrent_registration_has_single_identity_and_no_partial_row(self):
        barrier=threading.Barrier(2);results=[];errors=[]
        def register():
            try:
                client=self.app.test_client();barrier.wait(timeout=5)
                r=client.post('/users',json={'name':'Concurrent','email':'concurrent@example.test','password':self.password})
                results.append(r.status_code)
            except BaseException as error: errors.append(type(error).__name__)
        threads=[threading.Thread(target=register) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads));self.assertFalse(errors)
        self.assertEqual(sorted(results),[201,409])
        self.assertEqual(self.count(User),5)

    def test_factory_import_config_isolation_and_context_cleanup(self):
        otherpath=Path(self.temp.name)/'other.db'
        other=create_app({'SECRET_KEY':secrets.token_urlsafe(48),'SQLALCHEMY_DATABASE_URI':'sqlite:///'+str(otherpath)})
        self.assertFalse(otherpath.exists())
        with other.app_context():
            db.create_all();self.assertEqual(db.session.scalar(select(func.count()).select_from(User)),0)
            db.session.remove();db.engine.dispose()
        self.assertEqual(self.count(User),4)
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'TASK_SECRET_KEY'): create_app()
        with self.assertRaisesRegex(RuntimeError,'TOKEN_MAX_AGE'):
            create_app({'SECRET_KEY':'a'*40,'TOKEN_MAX_AGE':0})
        module_dir=str(Path(__file__).resolve().parents[1])
        env={**os.environ,'PYTHONPATH':module_dir}
        env.pop('TASK_SECRET_KEY',None)
        proc=subprocess.run([sys.executable,'-c','import app; print("import-only")'],cwd=self.temp.name,env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(proc.returncode,0);self.assertEqual(proc.stdout.strip(),'import-only')
        self.assertFalse((Path(self.temp.name)/'instance').exists())
        with self.app.app_context(): engine=db.engine
        self.assertEqual(engine.pool.checkedout(),0)


if __name__=='__main__': unittest.main()
