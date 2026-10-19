// Disposable fixture process only; not loaded by the production entry point.
const { start } = require('../src/server');
const { openDatabase } = require('../src/database');
const { loadConfig } = require('../src/config');

start({
    config: loadConfig(),
    databaseFactory: async config => {
        const database = await openDatabase(config);
        const seedHash = database.prepare('SELECT pass FROM users WHERE id = 1').get().pass;
        database.prepare('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)')
            .run('Unlinked Fixture', 'unlinked@example.test', seedHash);
        return database;
    },
}).then(runtime => {
    process.on('message', message => {
        if (message === 'snapshot') {
            process.send({ snapshot: {
                users: runtime.database.prepare('SELECT COUNT(*) AS n FROM users').get().n,
                unlinked: runtime.database.prepare('SELECT COUNT(*) AS n FROM users WHERE id = 2').get().n,
                foreignKeyErrors: runtime.database.pragma('foreign_key_check').length,
            } });
        }
    });
    const stop = () => runtime.stop().then(() => { if (process.connected) process.disconnect(); });
    process.once('SIGTERM', stop);
    process.once('SIGINT', stop);
}).catch(() => {
    process.stderr.write('fixture_startup_failed\n');
    process.exitCode = 1;
});
