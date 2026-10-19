const { AppError } = require('../services/errors');

function errorHandler(logger) {
    return (error, req, res, next) => {
        if (res.headersSent) return next(error);
        if (error instanceof AppError) {
            return res.status(error.status).json({ error: { code: error.code, message: error.message } });
        }
        if (error.type === 'entity.parse.failed') {
            return res.status(400).json({ error: { code: 'INVALID_JSON', message: 'JSON inválido' } });
        }
        if (error.type === 'entity.too.large') {
            return res.status(413).json({ error: { code: 'PAYLOAD_TOO_LARGE', message: 'Corpo excede 16 KiB' } });
        }
        if (['charset.unsupported', 'encoding.unsupported'].includes(error.type)) {
            return res.status(415).json({ error: { code: 'UNSUPPORTED_ENCODING', message: 'Codificação não suportada' } });
        }
        // Never log error.message, SQL, request bodies, headers or raw identifiers.
        const category = typeof error.code === 'string' && /^SQLITE_[A-Z_]+$/.test(error.code) ? error.code : 'UNEXPECTED';
        logger.error({ event: 'request_failed', category });
        return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Erro interno' } });
    };
}

module.exports = { errorHandler };
