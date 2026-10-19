const Database = require('better-sqlite3');
const passwords = require('../security/passwords');

const SCHEMA = `
CREATE TABLE users (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL,
 email TEXT NOT NULL UNIQUE CHECK(email = lower(trim(email))), pass TEXT NOT NULL
);
CREATE TABLE courses (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, price REAL NOT NULL CHECK(price >= 0),
 active INTEGER NOT NULL CHECK(active IN (0, 1))
);
CREATE TABLE enrollments (
 id INTEGER PRIMARY KEY,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE RESTRICT
);
CREATE TABLE payments (
 id INTEGER PRIMARY KEY,
 enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE RESTRICT,
 amount REAL NOT NULL CHECK(amount >= 0), status TEXT NOT NULL
);
CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT NOT NULL, created_at DATETIME NOT NULL);
CREATE INDEX enrollments_user ON enrollments(user_id);
CREATE INDEX enrollments_course ON enrollments(course_id);
CREATE INDEX payments_enrollment ON payments(enrollment_id);
`;

async function openDatabase({ seedDemo = false, seedPassword } = {}, { onStatement } = {}) {
    // No existing file is opened or migrated: the approved storage is volatile.
    if (seedDemo && (typeof seedPassword !== 'string' || seedPassword.length < 8 || seedPassword.length > 128)) {
        throw new Error('Senha de seed inválida');
    }
    const seedHash = seedDemo ? await passwords.hash(seedPassword) : null;
    const database = new Database(':memory:', onStatement ? { verbose: onStatement } : {});
    try {
        database.pragma('foreign_keys = ON');
        database.transaction(() => {
            database.exec(SCHEMA);
            if (seedDemo) {
                database.prepare('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)')
                    .run('Demo Student', 'demo@example.test', seedHash);
                database.prepare('INSERT INTO courses (title, price, active) VALUES (?, ?, ?)')
                    .run('Clean Architecture', 997, 1);
                database.prepare('INSERT INTO courses (title, price, active) VALUES (?, ?, ?)')
                    .run('Docker', 497, 1);
                database.prepare('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)').run(1, 1);
                database.prepare('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)').run(1, 997, 'PAID');
            }
        })();
        return database;
    } catch (error) {
        database.close();
        throw error;
    }
}

module.exports = { openDatabase };
