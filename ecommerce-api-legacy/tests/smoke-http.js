const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');
const { once } = require('node:events');
const { createInterface } = require('node:readline');
const { writeFileSync } = require('node:fs');
const path = require('node:path');
const Database = require('better-sqlite3');

const root = path.resolve(__dirname, '..');
const token = randomBytes(32).toString('hex');
const password = randomBytes(16).toString('hex');
const card = '4000000000000000';
const cases = [];
const processes = [];
const evidence = {
    date: new Date().toISOString(), command: 'npm run test:http -- <evidence-path>',
    runtime: process.version, express: require('express/package.json').version,
    driver: { name: 'better-sqlite3', version: require('better-sqlite3/package.json').version },
    isolation: 'in-memory databases, synthetic data, loopback ephemeral ports; no external payment calls',
    cases, processes,
};
const versionDb = new Database(':memory:');
evidence.sqlite = versionDb.prepare('SELECT sqlite_version() AS version').get().version;
versionDb.close();

async function launch(entry) {
    const child = spawn(process.execPath, [entry], {
        cwd: root,
        env: { ...process.env, ADMIN_TOKEN: token, SEED_DEMO: 'true', SEED_PASSWORD: password, HOST: '127.0.0.1', PORT: '0' },
        stdio: ['ignore', 'pipe', 'pipe', 'ipc'],
    });
    const record = { command: `node ${entry}`, pid: child.pid, logs: [], stopped: false };
    processes.push(record);
    const lines = createInterface({ input: child.stdout });
    child.stderr.on('data', data => record.logs.push(data.toString()));
    const ready = await new Promise((resolve, reject) => {
        const timer = setTimeout(() => { child.kill('SIGKILL'); reject(new Error('Readiness timeout')); }, 15000);
        child.once('error', error => { clearTimeout(timer); reject(error); });
        child.once('exit', code => { clearTimeout(timer); reject(new Error(`Exited before ready (${code})`)); });
        lines.on('line', line => {
            record.logs.push(line);
            try {
                const data = JSON.parse(line);
                if (data.event === 'ready') { clearTimeout(timer); resolve(data); }
            } catch { /* Non-JSON diagnostic is retained and checked for secrets before output. */ }
        });
    });
    assert.equal(ready.pid, child.pid);
    assert.equal(child.exitCode, null);
    record.port = ready.port;
    const base = `http://127.0.0.1:${ready.port}`;
    return {
        child, base,
        async stop() {
            const closed = once(child, 'close');
            child.kill('SIGTERM');
            const timer = setTimeout(() => child.kill('SIGKILL'), 7000);
            const [code, signal] = await closed;
            clearTimeout(timer);
            lines.close();
            record.stopped = true;
            record.exitCode = code;
            record.signal = signal;
            assert.equal(code, 0);
        },
    };
}

async function request(server, name, method, route, expected, { body, admin = false, raw, headers = {} } = {}) {
    const response = await fetch(server.base + route, {
        method, headers: { ...(body !== undefined || raw !== undefined ? { 'Content-Type': 'application/json' } : {}), ...(admin ? { Authorization: `Bearer ${token}` } : {}), ...headers },
        body: raw !== undefined ? raw : body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(5000),
    });
    const data = await response.json();
    cases.push({ name, method, path: route, expected, observed: response.status, body: data });
    assert.equal(response.status, expected, name);
    if (expected >= 400) {
        assert.equal(typeof data.error.code, 'string');
        assert.equal(typeof data.error.message, 'string');
    }
    return data;
}

async function main() {
    const server = await launch('src/server.js');
    try {
        await request(server, 'report requires admin', 'GET', '/api/admin/financial-report', 401);
        await request(server, 'report rejects incorrect admin', 'GET', '/api/admin/financial-report', 401, { headers: { Authorization: 'Bearer invalid' } });
        const initial = await request(server, 'initial authorized report', 'GET', '/api/admin/financial-report', 200, { admin: true });
        assert.deepEqual(initial, [
            { course: 'Clean Architecture', revenue: 997, students: [{ student: 'Demo Student', paid: 997 }] },
            { course: 'Docker', revenue: 0, students: [] },
        ]);
        const payload = { usr: ' HTTP Student ', eml: ' HTTP@EXAMPLE.TEST ', pwd: password, c_id: 2, card };
        const created = await request(server, 'new checkout commits', 'POST', '/api/checkout', 200, { body: payload });
        assert.deepEqual(created, { msg: 'Sucesso', enrollment_id: 2 });
        await request(server, 'existing user authenticates', 'POST', '/api/checkout', 200, { body: { ...payload, eml: 'http@example.test' } });
        await request(server, 'existing user wrong password', 'POST', '/api/checkout', 401, { body: { ...payload, pwd: 'invalid-password' } });
        await request(server, 'denied payment', 'POST', '/api/checkout', 400, { body: { ...payload, eml: 'denied@example.test', card: '5000000000000000' } });
        await request(server, 'course missing', 'POST', '/api/checkout', 404, { body: { ...payload, c_id: 999 } });
        for (const [name, body] of [
            ['missing fields', {}], ['numeric card', { ...payload, card: 4000000000000000 }],
            ['object card', { ...payload, card: {} }], ['array body', []], ['null body', null],
            ['string course id', { ...payload, c_id: '2' }], ['missing password', { ...payload, pwd: undefined }],
        ]) await request(server, name, 'POST', '/api/checkout', 400, { body });
        await request(server, 'malformed JSON', 'POST', '/api/checkout', 400, { raw: '{' });
        await request(server, 'oversized JSON', 'POST', '/api/checkout', 413, { body: { oversized: 'x'.repeat(17000) } });
        await request(server, 'unsupported JSON charset', 'POST', '/api/checkout', 415, { raw: '{}', headers: { 'Content-Type': 'application/json; charset=unknown' } });
        await request(server, 'delete requires admin', 'DELETE', '/api/users/1', 401);
        await request(server, 'delete rejects incorrect admin', 'DELETE', '/api/users/1', 401, { headers: { Authorization: 'Bearer invalid' } });
        await request(server, 'delete enrolled user preserves history', 'DELETE', '/api/users/1', 409, { admin: true });
        await request(server, 'delete missing user', 'DELETE', '/api/users/999', 404, { admin: true });
        await request(server, 'delete invalid id', 'DELETE', '/api/users/abc', 400, { admin: true });
        const after = await request(server, 'report confirms only successful checkout effects', 'GET', '/api/admin/financial-report', 200, { admin: true });
        assert.equal(after[1].revenue, 994);
        assert.deepEqual(after[1].students, [{ student: 'HTTP Student', paid: 497 }, { student: 'HTTP Student', paid: 497 }]);
        assert.equal(after[0].revenue, 997);
        evidence.httpEffects = { successfulNewUserEnrollments: 2, course2Revenue: 994, originalHistoryPreserved: true };
    } finally { await server.stop(); }

    const fixture = await launch('tests/http-fixture.js');
    try {
        await request(fixture, 'delete unlinked fixture user succeeds', 'DELETE', '/api/users/2', 200, { admin: true });
        await request(fixture, 'deleted user is now absent', 'DELETE', '/api/users/2', 404, { admin: true });
        const snapshot = await new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error('Snapshot timeout')), 5000);
            fixture.child.once('message', message => { clearTimeout(timer); resolve(message.snapshot); });
            fixture.child.send('snapshot');
        });
        assert.deepEqual(snapshot, { users: 1, unlinked: 0, foreignKeyErrors: 0 });
        evidence.deleteDatabaseEffects = snapshot;
    } finally { await fixture.stop(); }
    evidence.verifiedEndpoints = 3;
    evidence.passed = true;
}

main().catch(error => {
    evidence.passed = false;
    // No request body, token, password, driver diagnostics or stack in artifacts.
    evidence.failure = { type: error.name, code: error.code || 'VALIDATION_FAILED' };
    process.exitCode = 1;
}).finally(() => {
    const raw = JSON.stringify(evidence);
    const secrets = [token, password, card];
    evidence.logsContainSecrets = secrets.some(secret => raw.includes(secret));
    if (evidence.logsContainSecrets) { evidence.passed = false; process.exitCode = 1; }
    let safe = JSON.stringify(evidence, null, 2);
    for (const secret of secrets) safe = safe.split(secret).join('[REDACTED]');
    if (process.argv[2]) writeFileSync(path.resolve(process.argv[2]), safe + '\n');
    console.log(JSON.stringify({ passed: evidence.passed, cases: cases.length, endpoints: evidence.verifiedEndpoints || 0, processesStopped: processes.every(p => p.stopped), logsContainSecrets: evidence.logsContainSecrets }));
});
