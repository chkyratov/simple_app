from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Явно указываем имя таблицы
    
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    verification_code = db.Column(db.String(6), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    access_token = db.Column(db.String(500), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    employee_id = db.Column(db.Integer, nullable=True)
    expired_time = db.Column(db.DateTime, nullable=True)
    token_created_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_token_valid(self):
        """Проверка валидности токена"""
        if not self.access_token or not self.expired_time:
            return False
        return datetime.utcnow() < self.expired_time
    
    def get_id(self):
        """Метод, необходимый для Flask-Login"""
        return str(self.id)
    
    def __repr__(self):
        return f'<User {self.phone_number}>'

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('requests', lazy=True))
    
    def __repr__(self):
        return f'<Request {self.title}>'
