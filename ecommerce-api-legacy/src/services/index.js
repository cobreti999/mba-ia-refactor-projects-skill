const { AppError } = require('./errors');
const { demoPaymentGateway } = require('./payment');

function createServices({ repository, passwords, paymentGateway = demoPaymentGateway }) {
    return {
        async checkout({ userName, email, password, courseId, card }) {
            if (!repository.findCourse(courseId)) throw new AppError('COURSE_NOT_FOUND', 'Curso não encontrado', 404);
            const user = repository.findUserByEmail(email);
            if (user && !await passwords.verify(password, user.pass)) {
                throw new AppError('INVALID_CREDENTIALS', 'Credenciais inválidas', 401);
            }
            if (!user && password.length < 8) throw new AppError('INVALID_INPUT', 'Senha deve conter de 8 a 128 caracteres', 400);
            if (!paymentGateway.approve(card)) throw new AppError('PAYMENT_DENIED', 'Pagamento recusado', 400);
            const passwordHash = user ? null : await passwords.hash(password);
            // No await inside this transaction: requests cannot interleave writes.
            return repository.transaction(() => {
                const course = repository.findCourse(courseId);
                if (!course) throw new AppError('COURSE_NOT_FOUND', 'Curso não encontrado', 404);
                const currentUser = repository.findUserByEmail(email);
                if (!user && currentUser) throw new AppError('USER_CONFLICT', 'Cadastro concorrente; repita com suas credenciais', 409);
                if (user && (!currentUser || currentUser.id !== user.id || currentUser.pass !== user.pass)) {
                    throw new AppError('INVALID_CREDENTIALS', 'Credenciais inválidas', 401);
                }
                const userId = user ? user.id : repository.createUser(userName, email, passwordHash);
                const enrollmentId = repository.enroll(userId, courseId);
                repository.pay(enrollmentId, course.price, 'PAID');
                repository.audit(`Checkout curso ${courseId} por ${userId}`);
                return enrollmentId;
            });
        },
        financialReport() {
            const courses = new Map();
            for (const row of repository.financialRows()) {
                if (!courses.has(row.course_id)) courses.set(row.course_id, { course: row.title, revenue: 0, students: [] });
                const course = courses.get(row.course_id);
                if (row.enrollment_id !== null) {
                    if (row.status === 'PAID') course.revenue += row.amount;
                    course.students.push({ student: row.student ?? 'Unknown', paid: row.amount ?? 0 });
                }
            }
            return [...courses.values()];
        },
        deleteUser(id) {
            repository.transaction(() => {
                if (!repository.findUserById(id)) throw new AppError('USER_NOT_FOUND', 'Usuário não encontrado', 404);
                if (repository.hasEnrollments(id)) throw new AppError('USER_ENROLLED', 'Usuário possui matrículas', 409);
                repository.deleteUser(id);
            });
        },
    };
}

module.exports = { createServices };
