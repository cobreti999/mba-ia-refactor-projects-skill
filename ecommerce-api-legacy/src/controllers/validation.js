const { AppError } = require('../services/errors');

function invalid() { throw new AppError('INVALID_INPUT', 'Dados inválidos', 400); }

function checkoutInput(body) {
    if (!body || typeof body !== 'object' || Array.isArray(body)) invalid();
    const { usr, eml, pwd, c_id: courseId, card } = body;
    if (typeof usr !== 'string' || !usr.trim() || usr.trim().length > 200) invalid();
    if (typeof eml !== 'string' || eml.trim().length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(eml.trim())) invalid();
    if (typeof pwd !== 'string' || !pwd.length || pwd.length > 128) invalid();
    if (!Number.isSafeInteger(courseId) || courseId <= 0) invalid();
    if (typeof card !== 'string' || !/^\d{13,19}$/.test(card)) invalid();
    return { userName: usr.trim(), email: eml.trim().toLowerCase(), password: pwd, courseId, card };
}

function userIdInput(value) {
    if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(Number(value))) invalid();
    return Number(value);
}

module.exports = { checkoutInput, userIdInput };
