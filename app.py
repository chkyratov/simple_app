from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from models import db, User, Request
from auth_api import AuthAPI
from functools import wraps
import logging
import os
from datetime import datetime
import socket
import webbrowser
import threading
import time
from datetime import timedelta
#import database

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_ip_address():
    """Получение IP адреса компьютера"""
    try:
        # Пробуем получить IP через подключение к интернету
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            # Если не получилось, пробуем получить локальный IP
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except:
            # Если и это не получилось, возвращаем localhost
            return "127.0.0.1"

def open_browser():
    """Открытие браузера после небольшой задержки"""
    time.sleep(1.5)  # Ждем, пока сервер запустится
    webbrowser.open(f'http://{HOST}:{PORT}')

# Получаем абсолютный путь к папке instance
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
db_file = os.path.join(instance_path, 'auth.db')

app = Flask(__name__)
# Используем безопасный секретный ключ
app.config['SECRET_KEY'] = 'c91d76068b8e3a5d7805f132e45f1694b03f6698a9b35e39d0337d8e31b1c439'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Сессия живет 7 дней

# Инициализация базы данных
db.init_app(app)

# Создание всех таблиц, если их нет
with app.app_context():
    if not os.path.exists(db_file):
        logger.info("База данных не найдена. Создаем новую базу данных...")
        db.create_all()
        logger.info("База данных успешно создана")
    else:
        logger.info("База данных уже существует")

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создание экземпляра AuthAPI
auth_api = AuthAPI(db.session)

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
            
        # Проверяем срок действия токена
        if current_user.expired_time and current_user.expired_time < datetime.utcnow():
            logout_user()
            return redirect(url_for('login'))
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    # Если пользователь уже авторизован, перенаправляем на дашборд
    if current_user.is_authenticated and current_user.is_token_valid():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем на дашборд
    if current_user.is_authenticated and current_user.is_token_valid():
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            phone = data.get('phone')
        else:
            phone = request.form.get('phone')
            
        if not phone:
            return jsonify({'success': False, 'error': 'Номер телефона не указан'})
            
        # Очищаем номер от всего кроме цифр
        clean_phone = ''.join(filter(str.isdigit, phone))
        if clean_phone.startswith('8'):
            clean_phone = '7' + clean_phone[1:]
        if not clean_phone.startswith('7'):
            clean_phone = '7' + clean_phone
        formatted_phone = '+' + clean_phone
        
        result = auth_api.send_verification_code(formatted_phone)
        if result.get('success'):
            session['phone'] = formatted_phone
            return jsonify({'success': True, 'redirect': url_for('verify')})
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Ошибка отправки кода')})
            
    return render_template('login.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if not session.get('phone'):
        logger.error('Попытка доступа к verify без номера телефона в сессии')
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('verify.html')
        
    # POST запрос
    if request.is_json:
        data = request.get_json()
        code = data.get('code')
    else:
        code = request.form.get('code')
        
    if not code:
        return jsonify({'success': False, 'error': 'Код не указан'})
    
    try:
        result = auth_api.verify_code(session['phone'], code)
        if result.get('success'):
            # Получаем пользователя из базы
            user = User.query.filter_by(phone_number=session['phone']).first()
            if user and user.is_token_valid():
                # Устанавливаем remember=True для сохранения сессии после закрытия браузера
                login_user(user, remember=True)
                # Делаем сессию постоянной
                session.permanent = True
                logger.info(f'Успешная верификация для номера {session["phone"]}')
                return jsonify({'success': True, 'redirect': url_for('dashboard')})
            else:
                logger.error(f'Пользователь не найден или токен недействителен для номера {session["phone"]}')
                return jsonify({'success': False, 'error': 'Ошибка авторизации'})
        else:
            logger.error(f'Ошибка верификации для номера {session["phone"]}: {result.get("error")}')
            return jsonify({'success': False, 'error': result.get('error') or 'Ошибка верификации'})
    except Exception as e:
        logger.error(f'Исключение при верификации: {str(e)}')
        return jsonify({'success': False, 'error': 'Ошибка сервера'})

@app.route('/dashboard')
@token_required
def dashboard():
    if not current_user.is_authenticated or not current_user.is_token_valid():
        logout_user()
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/logout')
@token_required
def logout():
    user = current_user
    if user.is_authenticated:
        user.access_token = None
        user.expired_time = None
        db.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/complaint', methods=['GET', 'POST'])
def complaint():
    return render_template('complaint.html')

@app.route('/anonimous')
def anonimous():
    return render_template('anonimous.html')

@app.route('/new_request', methods=['GET', 'POST'])
@token_required
def new_request():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            return jsonify({'success': False, 'error': 'Заголовок обязателен'})
            
        try:
            new_req = Request(
                user_id=current_user.id,
                title=title,
                description=description
            )
            db.session.add(new_req)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Заявка создана'})
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при создании заявки: {str(e)}')
            return jsonify({'success': False, 'error': 'Ошибка при создании заявки'})
            
    return render_template('new_request.html')

if __name__ == '__main__':
    HOST = get_ip_address()
    PORT = 5000
    #database.created()
    print(f"\nServer running at: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop\n")
    
    # Запускаем браузер в отдельном потоке
    #threading.Thread(target=open_browser).start()
    
    # Запускаем сервер
    app.run(host=HOST, port=PORT, debug=True)
