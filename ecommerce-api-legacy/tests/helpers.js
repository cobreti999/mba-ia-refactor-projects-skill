const { randomBytes } = require('node:crypto');
const { openDatabase } = require('../src/database');
const { createRepository } = require('../src/models');
const { createServices } = require('../src/services');
const passwords = require('../src/security/passwords');

async function fixture(t, { seeded = true, onStatement } = {}) {
    const password = randomBytes(16).toString('hex');
    const config = { adminToken: randomBytes(32).toString('hex'), seedDemo: seeded, seedPassword: password, host: '127.0.0.1', port: 0 };
    const database = await openDatabase(config, { onStatement });
    t.after(() => { if (database.open) database.close(); });
    const repository = createRepository(database);
    return { database, repository, config, password, services: createServices({ repository, passwords }) };
}

function checkout(password, overrides = {}) {
    return { userName: 'Synthetic Student', email: 'student@example.test', password, courseId: 2, card: '4000000000000000', ...overrides };
}

function counts(database) {
    return Object.fromEntries(['users', 'enrollments', 'payments', 'audit_logs'].map(table => [table, database.prepare(`SELECT COUNT(*) AS count FROM ${table}`).get().count]));
}

module.exports = { fixture, checkout, counts };
