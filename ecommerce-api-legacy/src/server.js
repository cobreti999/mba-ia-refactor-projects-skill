const { loadConfig } = require('./config');
const { openDatabase } = require('./database');
const { createApp } = require('./app');

async function start({ config = loadConfig(), logger = console, databaseFactory = openDatabase } = {}) {
    const database = await databaseFactory(config);
    let server;
    try {
        const app = createApp({ database, config, logger });
        server = await new Promise((resolve, reject) => {
            const listener = app.listen(config.port, config.host, () => resolve(listener));
            listener.once('error', reject);
        });
    } catch (error) {
        database.close();
        throw error;
    }
    let closing;
    const stop = () => {
        if (!closing) closing = new Promise(resolve => {
            server.close(() => {
                clearTimeout(deadline);
                database.close();
                resolve();
            });
            const deadline = setTimeout(() => server.closeAllConnections(), 5000);
            deadline.unref();
        });
        return closing;
    };
    logger.log(JSON.stringify({ event: 'ready', host: config.host, port: server.address().port, pid: process.pid }));
    return { server, database, stop };
}

if (require.main === module) {
    start().then(runtime => {
        const shutdown = () => runtime.stop().then(() => { process.exitCode = 0; });
        process.once('SIGINT', shutdown);
        process.once('SIGTERM', shutdown);
    }).catch(() => {
        // Failure details may contain credentials; print only operational guidance.
        console.error(JSON.stringify({ event: 'startup_failed', message: 'Verifique Node, ADMIN_TOKEN, PORT, SEED_DEMO, SEED_PASSWORD e disponibilidade do banco/porta' }));
        process.exitCode = 1;
    });
}

module.exports = { start };
