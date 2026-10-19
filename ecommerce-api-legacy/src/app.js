const express = require('express');
const { createControllers } = require('./controllers');
const { registerRoutes } = require('./routes');
const { createServices } = require('./services');
const { createRepository } = require('./models');
const passwords = require('./security/passwords');
const { requireAdmin } = require('./middleware/auth');
const { errorHandler } = require('./middleware/errors');
const { AppError } = require('./services/errors');

// Importing this module opens neither a database nor an HTTP listener.
function createApp({ database, config, logger = console, paymentGateway }) {
    const app = express();
    app.disable('x-powered-by');
    app.use(express.json({ limit: '16kb' }));
    const repository = createRepository(database);
    const services = createServices({ repository, passwords, paymentGateway });
    registerRoutes(app, createControllers(services), requireAdmin(config.adminToken));
    app.use((req, res, next) => next(new AppError('NOT_FOUND', 'Recurso não encontrado', 404)));
    app.use(errorHandler(logger));
    return app;
}

module.exports = { createApp };
