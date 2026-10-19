function loadConfig(env = process.env) {
    const adminToken = env.ADMIN_TOKEN;
    if (typeof adminToken !== 'string' || adminToken.length < 32 || /\s/.test(adminToken)) {
        throw new Error('ADMIN_TOKEN deve conter pelo menos 32 caracteres sem espaços');
    }
    const portText = env.PORT ?? '3000';
    if (!/^\d+$/.test(portText) || Number(portText) > 65535) {
        throw new Error('PORT deve ser um inteiro de 0 a 65535');
    }
    if (env.SEED_DEMO !== undefined && !['true', 'false'].includes(env.SEED_DEMO)) {
        throw new Error('SEED_DEMO deve ser true ou false');
    }
    const seedDemo = env.SEED_DEMO === 'true';
    const seedPassword = env.SEED_PASSWORD;
    if (seedDemo && (typeof seedPassword !== 'string' || seedPassword.length < 8 || seedPassword.length > 128)) {
        throw new Error('SEED_PASSWORD deve conter de 8 a 128 caracteres no modo demo');
    }
    return Object.freeze({ adminToken, port: Number(portText), host: env.HOST || '127.0.0.1', seedDemo, seedPassword });
}

module.exports = { loadConfig };
