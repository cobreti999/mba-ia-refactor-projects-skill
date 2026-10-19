class UserRepository:
    def __init__(self, connection):
        self.connection = connection

    def get(self, user_id):
        return self.connection.execute('SELECT * FROM usuarios WHERE id=?', (user_id,)).fetchone()

    def by_email(self, email):
        return self.connection.execute('SELECT * FROM usuarios WHERE email=? ORDER BY id', (email,)).fetchone()

    def list(self):
        return self.connection.execute('SELECT * FROM usuarios ORDER BY id').fetchall()

    def create(self, name, email, password_hash, role='cliente'):
        return self.connection.execute(
            "INSERT INTO usuarios(nome,email,senha,tipo,senha_format) VALUES (?,?,?,?,'werkzeug')",
            (name, email, password_hash, role),
        ).lastrowid

    def legacy_passwords(self):
        return self.connection.execute("SELECT id, senha FROM usuarios WHERE senha_format='plaintext'").fetchall()

    def set_password_hash(self, user_id, password_hash):
        self.connection.execute("UPDATE usuarios SET senha=?, senha_format='werkzeug' WHERE id=?", (password_hash, user_id))
