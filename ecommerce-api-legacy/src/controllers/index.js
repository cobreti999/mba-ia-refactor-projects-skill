const { checkoutInput, userIdInput } = require('./validation');

function createControllers(services) {
    return {
        async checkout(req, res) {
            const enrollmentId = await services.checkout(checkoutInput(req.body));
            res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
        },
        financialReport(req, res) {
            res.json(services.financialReport());
        },
        deleteUser(req, res) {
            services.deleteUser(userIdInput(req.params.id));
            res.status(200).json({ msg: 'Usuário deletado' });
        },
    };
}

module.exports = { createControllers };
