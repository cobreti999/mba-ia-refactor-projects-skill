const test = require('node:test');
const assert = require('node:assert/strict');
const { randomBytes } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { once } = require('node:events');
const { fixture, checkout, counts } = require('./helpers');
const passwords = require('../src/security/passwords');
const { checkoutInput, userIdInput } = require('../src/controllers/validation');
const { loadConfig } = require('../src/config');
const { createApp } = require('../src/app');
const { start } = require('../src/server');

test('scrypt uses independent salts, verifies credentials and rejects legacy formats', async () => {
    const password = randomBytes(16).toString('hex');
    const first = await passwords.hash(password);
    const second = await passwords.hash(password);
    assert.notEqual(first, second);
    assert.equal(await passwords.verify(password, first), true);
    assert.equal(await passwords.verify(password + 'x', first), false);
    for (const legacy of ['legacy-invalid', password, 'scrypt$999999999$8$1$bad$bad']) {
        assert.equal(await passwords.verify(password, legacy), false);
    }
});

test('config requires explicit credentials and bounded valid options', () => {
    const env = { ADMIN_TOKEN: randomBytes(32).toString('hex') };
    assert.equal(loadConfig(env).seedDemo, false);
    for (const patch of [{ ADMIN_TOKEN: '' }, { PORT: '-1' }, { PORT: '65536' }, { PORT: 'nan' }, { SEED_DEMO: 'yes' }, { SEED_DEMO: 'true' }]) {
        assert.throws(() => loadConfig({ ...env, ...patch }));
    }
    assert.equal(loadConfig({ ...env, PORT: '0' }).port, 0);
});

test('validation handles types, boundaries, normalization and public keys', () => {
    const valid = { usr: ' Student ', eml: ' STUDENT@EXAMPLE.TEST ', pwd: 'synthetic-password', c_id: 1, card: '4000000000000000' };
    assert.equal(checkoutInput(valid).email, 'student@example.test');
    assert.equal(checkoutInput(valid).userName, 'Student');
    for (const body of [null, [], 1, {}, ...[
        { usr: '' }, { usr: {} }, { usr: 'x'.repeat(201) }, { eml: 'bad' }, { eml: 1 },
        { eml: 'a'.repeat(250) + '@x.test' }, { pwd: undefined }, { pwd: 123 }, { pwd: 'x'.repeat(129) },
        { c_id: '1' }, { c_id: -1 }, { c_id: 1.5 }, { c_id: Number.MAX_SAFE_INTEGER + 1 },
        { card: 4000000000000000 }, { card: {} }, { card: '4'.repeat(12) }, { card: '4'.repeat(20) },
    ].map(patch => ({ ...valid, ...patch }))]) assert.throws(() => checkoutInput(body), { status: 400 });
    for (const length of [13, 19]) assert.equal(checkoutInput({ ...valid, card: '4'.repeat(length) }).card.length, length);
    for (const id of ['0', '-1', '1x', '1.2', '999999999999999999999']) assert.throws(() => userIdInput(id), { status: 400 });
    assert.equal(userIdInput('2'), 2);
});

test('checkout commits user, enrollment, payment and audit with original response semantics', async t => {
    const f = await fixture(t);
    const before = counts(f.database);
    const id = await f.services.checkout(checkout(f.password));
    assert.equal(id, 2);
    const after = counts(f.database);
    for (const table of Object.keys(before)) assert.equal(after[table], before[table] + 1);
    const user = f.repository.findUserByEmail('student@example.test');
    assert.equal(await passwords.verify(f.password, user.pass), true);
    assert.equal(f.services.financialReport()[1].revenue, 497);
    await f.services.checkout(checkout(f.password));
    assert.equal(counts(f.database).users, after.users);
    assert.equal(f.services.financialReport()[1].students.length, 2);
});

test('denied payment, invalid credentials and missing/inactive courses leave no writes', async t => {
    const f = await fixture(t);
    const before = counts(f.database);
    for (const [patch, status] of [
        [{ card: '5000000000000000' }, 400],
        [{ email: 'demo@example.test', password: 'incorrect-password' }, 401],
        [{ courseId: 999 }, 404], [{ password: 'short' }, 400],
    ]) await assert.rejects(f.services.checkout(checkout(f.password, patch)), { status });
    f.database.prepare('UPDATE courses SET active = 0 WHERE id = 2').run();
    await assert.rejects(f.services.checkout(checkout(f.password)), { status: 404 });
    assert.deepEqual(counts(f.database), before);
});

for (const table of ['users', 'enrollments', 'payments', 'audit_logs']) {
    test(`rollback leaves all tables unchanged when ${table} insertion fails`, async t => {
        const f = await fixture(t);
        const before = counts(f.database);
        f.database.exec(`CREATE TRIGGER fail_write BEFORE INSERT ON ${table} BEGIN SELECT RAISE(ABORT, 'injected failure'); END`);
        await assert.rejects(f.services.checkout(checkout(f.password)));
        assert.deepEqual(counts(f.database), before);
    });
}

test('concurrent signup cannot create duplicate identities or partial transactions', async t => {
    const f = await fixture(t);
    const results = await Promise.allSettled([f.services.checkout(checkout(f.password)), f.services.checkout(checkout(f.password))]);
    assert.equal(results.filter(r => r.status === 'fulfilled').length, 1);
    assert.equal(results.find(r => r.status === 'rejected').reason.status, 409);
    assert.deepEqual(counts(f.database), { users: 2, enrollments: 2, payments: 2, audit_logs: 1 });
    const existing = await Promise.all([f.services.checkout(checkout(f.password)), f.services.checkout(checkout(f.password))]);
    assert.equal(new Set(existing).size, 2);
    assert.equal(counts(f.database).users, 2);
});

test('delete preserves enrolled users and history; nonexistent and unlinked users have distinct outcomes', async t => {
    const f = await fixture(t);
    assert.throws(() => f.services.deleteUser(1), { status: 409 });
    assert.throws(() => f.services.deleteUser(999), { status: 404 });
    const id = f.repository.createUser('Unlinked', 'unlinked@example.test', await passwords.hash(f.password));
    f.services.deleteUser(id);
    assert.equal(f.repository.findUserById(id), undefined);
    assert.throws(() => f.database.prepare('DELETE FROM users WHERE id = 1').run(), error =>
        error.code.startsWith('SQLITE_CONSTRAINT_') && error.message === 'FOREIGN KEY constraint failed');
    assert.throws(() => f.repository.enroll(999, 1), { code: 'SQLITE_CONSTRAINT_FOREIGNKEY' });
    assert.equal(f.database.pragma('foreign_key_check').length, 0);
});

test('report preserves empty courses, unpaid enrollment, denied amount and deterministic ordering in one statement', async t => {
    let queries = 0;
    // Count actual SELECT/CTE executions from SQLite; never retain bound SQL values.
    const f = await fixture(t, { onStatement: sql => { if (/^\s*(SELECT|WITH)\b/i.test(sql)) queries++; } });
    queries = 0;
    assert.deepEqual(f.services.financialReport()[1], { course: 'Docker', revenue: 0, students: [] });
    const enrollment = f.repository.enroll(1, 2);
    assert.deepEqual(f.services.financialReport()[1].students, [{ student: 'Demo Student', paid: 0 }]);
    f.repository.pay(enrollment, 25, 'DENIED');
    f.repository.pay(enrollment, 999, 'PAID'); // first payment semantics; no multiplied rows
    const denied = f.services.financialReport()[1];
    assert.equal(denied.revenue, 0);
    assert.equal(denied.students[0].paid, 25);
    for (let index = 0; index < 30; index++) {
        const id = f.repository.enroll(1, 2);
        f.repository.pay(id, 497, 'PAID');
    }
    const report = f.services.financialReport();
    assert.equal(report[1].revenue, 30 * 497);
    assert.equal(report[1].students.length, 31);
    assert.equal(queries, 4); // Four report calls, irrespective of increasing cardinality.
});

test('independent app databases do not share mutable state', async t => {
    const first = await fixture(t);
    const second = await fixture(t);
    await first.services.checkout(checkout(first.password));
    assert.equal(counts(second.database).users, 1);
    assert.equal(second.services.financialReport()[1].revenue, 0);
});

test('schema initialization failure and listener failure close resources without a ready event', async t => {
    const logs = [];
    const logger = { log: value => logs.push(value), error: value => logs.push(value) };
    const config = { adminToken: randomBytes(32).toString('hex'), port: 0, host: '127.0.0.1' };
    await assert.rejects(start({ config, logger, databaseFactory: async () => { throw new Error('injected initialization'); } }));
    assert.equal(logs.length, 0);
    const running = await start({ config, logger });
    t.after(() => running.stop());
    let failedDatabase;
    const { openDatabase } = require('../src/database');
    await assert.rejects(start({
        config: { ...config, port: running.server.address().port }, logger,
        databaseFactory: async () => { failedDatabase = await openDatabase(); return failedDatabase; },
    }), { code: 'EADDRINUSE' });
    assert.equal(failedDatabase.open, false);
    await running.stop();
    assert.equal(running.database.open, false);
});

test('HTTP error boundary sanitizes malformed JSON, DB failures and credentials; DELETE success checked against DB', async t => {
    const f = await fixture(t);
    const logs = [];
    const app = createApp({ database: f.database, config: f.config, logger: { error: value => logs.push(value) } });
    const server = app.listen(0, '127.0.0.1');
    await once(server, 'listening');
    t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
    const base = `http://127.0.0.1:${server.address().port}`;
    const auth = { Authorization: `Bearer ${f.config.adminToken}`, 'Content-Type': 'application/json' };
    let response = await fetch(base + '/api/checkout', { method: 'POST', headers: auth, body: '{"pwd":' });
    assert.equal(response.status, 400);
    assert.equal((await response.json()).error.code, 'INVALID_JSON');
    const unlinked = f.repository.createUser('Delete Me', 'delete@example.test', await passwords.hash(f.password));
    response = await fetch(base + `/api/users/${unlinked}`, { method: 'DELETE', headers: auth });
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { msg: 'Usuário deletado' });
    assert.equal(f.repository.findUserById(unlinked), undefined);
    f.database.exec("CREATE TRIGGER fail_audit BEFORE INSERT ON audit_logs BEGIN SELECT RAISE(ABORT, 'private diagnostic'); END");
    const payload = { usr: 'Student', eml: 'failure@example.test', pwd: f.password, c_id: 2, card: '4000000000000000' };
    response = await fetch(base + '/api/checkout', { method: 'POST', headers: auth, body: JSON.stringify(payload) });
    assert.equal(response.status, 500);
    assert.deepEqual(await response.json(), { error: { code: 'INTERNAL_ERROR', message: 'Erro interno' } });
    assert.equal(f.repository.findUserByEmail('failure@example.test'), undefined);
    f.database.close();
    response = await fetch(base + '/api/admin/financial-report', { headers: auth });
    assert.equal(response.status, 500);
    await response.json();
    response = await fetch(base + '/api/admin/financial-report');
    assert.equal(response.status, 401); // authorization is before the failed DB
    await response.json();
    const serialized = JSON.stringify(logs);
    for (const secret of [f.password, f.config.adminToken, payload.card, 'private diagnostic']) assert.equal(serialized.includes(secret), false);
    assert.equal(logs.length, 2);
});

test('missing boot configuration fails clearly, and importing app has no listener or seed effects', () => {
    const env = { ...process.env };
    delete env.ADMIN_TOKEN;
    const result = spawnSync(process.execPath, ['src/server.js'], { env, encoding: 'utf8', timeout: 5000 });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /startup_failed/);
    const imported = spawnSync(process.execPath, ['-e', "require('./src/app'); process.stdout.write('imported')"], { env, encoding: 'utf8', timeout: 5000 });
    assert.equal(imported.status, 0);
    assert.equal(imported.stdout, 'imported');
});
