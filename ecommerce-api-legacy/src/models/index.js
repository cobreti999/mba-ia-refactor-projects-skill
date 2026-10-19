function createRepository(database) {
    const statements = {
        course: database.prepare('SELECT id, title, price FROM courses WHERE id = ? AND active = 1'),
        userByEmail: database.prepare('SELECT id, name, email, pass FROM users WHERE email = ?'),
        userById: database.prepare('SELECT id FROM users WHERE id = ?'),
        insertUser: database.prepare('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)'),
        enroll: database.prepare('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)'),
        pay: database.prepare('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)'),
        audit: database.prepare("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))"),
        hasEnrollments: database.prepare('SELECT 1 FROM enrollments WHERE user_id = ? LIMIT 1'),
        deleteUser: database.prepare('DELETE FROM users WHERE id = ?'),
        report: database.prepare(`
            WITH first_payment AS (SELECT enrollment_id, MIN(id) AS id FROM payments GROUP BY enrollment_id)
            SELECT c.id AS course_id, c.title, e.id AS enrollment_id, u.name AS student,
                   p.amount, p.status
            FROM courses c
            LEFT JOIN enrollments e ON e.course_id = c.id
            LEFT JOIN users u ON u.id = e.user_id
            LEFT JOIN first_payment fp ON fp.enrollment_id = e.id
            LEFT JOIN payments p ON p.id = fp.id
            ORDER BY c.id, e.id
        `),
    };
    return {
        transaction: work => database.transaction(work)(),
        findCourse: id => statements.course.get(id),
        findUserByEmail: email => statements.userByEmail.get(email),
        findUserById: id => statements.userById.get(id),
        createUser: (name, email, hash) => Number(statements.insertUser.run(name, email, hash).lastInsertRowid),
        enroll: (userId, courseId) => Number(statements.enroll.run(userId, courseId).lastInsertRowid),
        pay: (enrollmentId, amount, status) => statements.pay.run(enrollmentId, amount, status),
        audit: action => statements.audit.run(action),
        hasEnrollments: userId => Boolean(statements.hasEnrollments.get(userId)),
        deleteUser: id => statements.deleteUser.run(id).changes,
        financialRows: () => statements.report.all(),
    };
}

module.exports = { createRepository };
