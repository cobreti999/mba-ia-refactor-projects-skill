const { scrypt: derive, randomBytes, timingSafeEqual } = require('node:crypto');
const { promisify } = require('node:util');

const scrypt = promisify(derive);
const COST = Object.freeze({ N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 });
const KEY_LENGTH = 64;

async function hash(password) {
    const salt = randomBytes(16).toString('hex');
    const key = await scrypt(password, salt, KEY_LENGTH, COST);
    return `scrypt$${COST.N}$${COST.r}$${COST.p}$${salt}$${key.toString('hex')}`;
}

async function verify(password, stored) {
    // Accept only our bounded format, never the old pseudo-hash or plaintext.
    if (typeof stored !== 'string' || !/^scrypt\$32768\$8\$1\$[a-f0-9]{32}\$[a-f0-9]{128}$/.test(stored)) return false;
    const parts = stored.split('$');
    const key = await scrypt(password, parts[4], KEY_LENGTH, COST);
    return timingSafeEqual(key, Buffer.from(parts[5], 'hex'));
}

module.exports = { hash, verify };
