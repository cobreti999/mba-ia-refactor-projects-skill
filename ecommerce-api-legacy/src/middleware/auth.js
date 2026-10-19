const { createHash, timingSafeEqual } = require('node:crypto');
const { AppError } = require('../services/errors');

const digest = value => createHash('sha256').update(value).digest();

function requireAdmin(token) {
    if (typeof token !== 'string' || token.length < 32 || /\s/.test(token)) throw new Error('Configuração administrativa inválida');
    const expected = digest(`Bearer ${token}`);
    return (req, res, next) => {
        if (!timingSafeEqual(digest(req.get('authorization') || ''), expected)) {
            return next(new AppError('UNAUTHORIZED', 'Credencial administrativa necessária', 401));
        }
        next();
    };
}

module.exports = { requireAdmin };
