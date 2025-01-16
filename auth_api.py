import requests
import logging
import re
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from models import User
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class AuthAPI:
    def __init__(self, db_session):
        """
        Инициализация API для аутентификации
        """
        self.base_url = "https://wms.wbwh.tech/srv/auth_phone_notification/api"
        self.session = requests.Session()
        self.session.request_timeout = 10  # таймаут в секундах
        self.db_session = db_session

    def send_verification_code(self, phone_number: str) -> dict:
        """
        Отправка кода подтверждения на номер телефона
        """
        try:
            # Форматируем номер телефона
            clean_phone = re.sub(r'\D', '', phone_number)
            formatted_phone = f"+7{clean_phone}" if not phone_number.startswith('+') else phone_number
            
            # Отправляем запрос на получение кода
            response = self.session.post(
                f"{self.base_url}/send_code",
                json={"phone_number": formatted_phone},
                timeout=self.session.request_timeout,
                verify=False  # Отключаем проверку SSL для тестового окружения
            )
            
            response.raise_for_status()
            logger.info(f"Код верификации отправлен на номер {formatted_phone}")
            return {"success": True}

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка подключения к серверу: {str(e)}")
            return {"success": False, "error": "Сервер временно недоступен. Попробуйте позже."}
        except requests.exceptions.Timeout as e:
            logger.error(f"Превышено время ожидания: {str(e)}")
            return {"success": False, "error": "Сервер не отвечает. Попробуйте позже."}
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка: {str(e)}")
            if e.response.status_code == 429:
                return {"success": False, "error": "Слишком много попыток. Попробуйте позже."}
            else:
                return {"success": False, "error": "Ошибка сервера. Попробуйте позже."}
        except requests.RequestException as e:
            logger.error(f"Error sending verification code: {str(e)}")
            return {"success": False, "error": "Произошла ошибка при отправке кода"}

    def verify_code(self, phone_number: str, code: str) -> dict:
        """
        Проверка кода подтверждения и сохранение данных пользователя
        """
        try:
            # Форматируем номер телефона
            clean_phone = re.sub(r'\D', '', phone_number)
            formatted_phone = f"+7{clean_phone}" if not phone_number.startswith('+') else phone_number
            
            # Отправляем запрос на проверку кода
            request_data = {
                "phone_number": formatted_phone,
                "code": int(code)
            }
            logger.info(f"Отправка запроса верификации: {request_data}")
            
            response = self.session.post(
                f"{self.base_url}/login",  
                json=request_data,
                timeout=self.session.request_timeout,
                verify=False
            )
            
            logger.info(f"Получен ответ: {response.status_code}")
            logger.info(f"Тело ответа: {response.text}")
            
            response.raise_for_status()
            auth_data = response.json()["data"]

            # Сохраняем или обновляем данные пользователя в базе
            try:
                user = self.db_session.query(User).filter_by(
                    phone_number=formatted_phone
                ).first()

                current_time = datetime.utcnow()
                token_expiry = current_time + timedelta(hours=24)

                if user:
                    # Обновляем существующего пользователя
                    user.access_token = auth_data["access_token"]
                    user.session_id = auth_data["session_id"]
                    user.employee_id = auth_data["employee_id"]
                    user.expired_time = token_expiry
                else:
                    # Создаем нового пользователя
                    user = User(
                        phone_number=formatted_phone,
                        access_token=auth_data["access_token"],
                        session_id=auth_data["session_id"],
                        employee_id=auth_data["employee_id"],
                        expired_time=token_expiry
                    )
                    self.db_session.add(user)

                self.db_session.commit()
                return {"success": True, "data": auth_data}

            except SQLAlchemyError as e:
                self.db_session.rollback()
                logger.error(f"Database error: {str(e)}")
                return {"success": False, "error": "Ошибка базы данных"}

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка подключения к серверу: {str(e)}")
            return {"success": False, "error": "Сервер временно недоступен. Попробуйте позже."}
        except requests.exceptions.Timeout as e:
            logger.error(f"Превышено время ожидания: {str(e)}")
            return {"success": False, "error": "Сервер не отвечает. Попробуйте позже."}
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка: {str(e)}")
            if e.response.status_code == 400:
                error_data = e.response.json()
                error_message = error_data.get('error', 'Неверный код подтверждения')
                return {"success": False, "error": error_message}
            elif e.response.status_code == 429:
                return {"success": False, "error": "Слишком много попыток. Попробуйте позже."}
            else:
                return {"success": False, "error": "Ошибка сервера. Попробуйте позже."}
        except requests.RequestException as e:
            logger.error(f"Error verifying code: {str(e)}")
            return {"success": False, "error": "Произошла ошибка при проверке кода"}

    def get_user_data(self, phone_number: str) -> dict:
        """
        Получение данных пользователя из базы с проверкой валидности токена
        """
        try:
            user = self.db_session.query(User).filter_by(
                phone_number=phone_number
            ).first()
            
            if not user:
                return {"success": False, "error": "User not found"}

            if not user.is_token_valid():
                return {"success": False, "error": "Token expired"}

            return {
                "success": True,
                "data": {
                    "phone_number": user.phone_number,
                    "access_token": user.access_token,
                    "session_id": user.session_id,
                    "employee_id": user.employee_id,
                    "expired_time": user.expired_time,
                    "token_created_at": user.token_created_at.isoformat() if user.token_created_at else None
                }
            }
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            return {"success": False, "error": "Database error"}

    def __del__(self):
        """
        Закрытие сессии при удалении объекта
        """
        if hasattr(self, 'session'):
            self.session.close()
