from database import db
from utils.clock import utc_now
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        if not isinstance(self.password, str) or not self.password.startswith(('scrypt:', 'pbkdf2:')):
            return False
        try:
            return check_password_hash(self.password, password)
        except (ValueError, TypeError):
            return False

    def is_admin(self):
        return self.role == 'admin'
