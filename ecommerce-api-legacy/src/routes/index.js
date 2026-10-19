const handle = controller => (req, res, next) => Promise.resolve().then(() => controller(req, res)).catch(next);

function registerRoutes(app, controllers, admin) {
    app.post('/api/checkout', handle(controllers.checkout));
    app.get('/api/admin/financial-report', admin, handle(controllers.financialReport));
    app.delete('/api/users/:id', admin, handle(controllers.deleteUser));
}

module.exports = { registerRoutes };
