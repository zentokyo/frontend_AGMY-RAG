import os
import uuid
import time
import logging
import requests
import threading
from typing import Optional
from dotenv import load_dotenv
from urllib3.exceptions import InsecureRequestWarning

load_dotenv()

logger = logging.getLogger(__name__)

# Конфигурируемый путь к CA-бандлу для SSL-верификации GigaChat API.
# По умолчанию False (без верификации) — для продакшена рекомендуется
# указать путь к сертификатам Минцифры через переменную окружения.
GIGACHAT_CA_BUNDLE = os.getenv("GIGACHAT_CA_BUNDLE", "")
GIGACHAT_VERIFY_SSL = GIGACHAT_CA_BUNDLE if GIGACHAT_CA_BUNDLE else False

if not GIGACHAT_VERIFY_SSL:
    import warnings
    warnings.filterwarnings("ignore", category=InsecureRequestWarning)


class GigaChatAuthError(Exception):
    """Кастомное исключение для ошибок аутентификации GigaChat"""
    pass


class GigaChatAuth:
    def __init__(self):
        self.auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.client_secret = os.getenv("GIGACHAT_AUTHORIZATION_KEY")
        self._access_token: Optional[str] = None
        self._expires_at: float = 0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 120:
            return self._access_token

        with self._lock:
            return self._refresh_token()

    def _refresh_token(self) -> str:
        # Если токен есть и он будет валиден еще как минимум 2 минуты
        if self._access_token and time.time() < self._expires_at - 120:
            return self._access_token
        if not self.client_secret:
            raise GigaChatAuthError("GIGACHAT_AUTHORIZATION_KEY не найден в .env")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {self.client_secret.strip()}",
        }
        data = {"scope": "GIGACHAT_API_PERS"}

        try:
            response = requests.post(
                self.auth_url, headers=headers, data=data,
                verify=GIGACHAT_VERIFY_SSL, timeout=15,
            )
            response.raise_for_status()
            res_data = response.json()

            self._access_token = res_data["access_token"]
            expires_in = res_data.get("expires_at", (time.time() + 1800) * 1000)
            self._expires_at = expires_in / 1000.0
            logger.info("GigaChat токен успешно обновлён, истекает через %.0f сек.",
                        self._expires_at - time.time())
            return self._access_token
        except requests.RequestException as e:
            logger.error("Ошибка получения токена GigaChat: %s", e)
            raise GigaChatAuthError(f"Ошибка API GigaChat при получении токена: {e}")


# Создаем глобальный экземпляр для кэширования внутри сессии
_auth_manager = GigaChatAuth()


def get_gigachat_token():
    return _auth_manager.get_token()
