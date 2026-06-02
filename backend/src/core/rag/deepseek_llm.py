import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

# Значения по умолчанию
DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


class DeepSeekFlashLLM:
    """Обёртка для DeepSeek V4 Flash API (OpenAI-совместимый).

    Конфигурация через переменные окружения:
      DEEPSEEK_API_KEY  — API-ключ (обязательно)
      DEEPSEEK_API_URL  — базовый URL (опционально, по умолчанию DEFAULT_API_URL)
      DEEPSEEK_MODEL    — имя модели (опционально, по умолчанию deepseek-chat)
    """

    def __init__(self):
        self.api_url = os.getenv("DEEPSEEK_API_URL", DEFAULT_API_URL)
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)
        self.max_tokens_default = int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))

        if not self.api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY не задан. Укажите ключ в .env "
                "или в переменной окружения."
            )

        logger.info(
            "DeepSeekFlashLLM инициализирован: model=%s, url=%s",
            self.model, self.api_url,
        )

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def invoke(self, prompt: str, max_tokens: int | None = None) -> str:
        """Отправить промпт и получить текстовый ответ."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or self.max_tokens_default,
            "temperature": 0.0,
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=payload,
                timeout=60,
            )
            if response.status_code != 200:
                logger.error(
                    "DeepSeek LLM error %d: %s",
                    response.status_code, response.text,
                )
                raise RuntimeError(
                    f"[DeepSeek Error] {response.status_code}: {response.text}"
                )
            return response.json()["choices"][0]["message"]["content"].strip()

        except requests.RequestException as e:
            logger.error("DeepSeek LLM request failed: %s", e)
            raise RuntimeError(f"[DeepSeek Network Error] {e}") from e

    def invoke_with_thinking(
        self, prompt: str, max_tokens: int | None = None,
    ) -> dict:
        """Отправить промпт и получить ответ с thinking-полем (High Thinking).

        Возвращает словарь:
          {"content": "...", "reasoning_content": "..."}
        """
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or self.max_tokens_default,
            "temperature": 0.0,
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=payload,
                timeout=120,  # Дольше — thinking может быть медленным
            )
            if response.status_code != 200:
                logger.error(
                    "DeepSeek LLM (thinking) error %d: %s",
                    response.status_code, response.text,
                )
                raise RuntimeError(
                    f"[DeepSeek Error] {response.status_code}: {response.text}"
                )

            choice = response.json()["choices"][0]
            message = choice["message"]
            result = {
                "content": message.get("content", "").strip(),
            }
            # DeepSeek возвращает reasoning_content при включённом thinking.
            # Если его нет — возвращаем пустую строку.
            result["reasoning_content"] = (
                message.get("reasoning_content", "") or ""
            ).strip()
            return result

        except requests.RequestException as e:
            logger.error("DeepSeek LLM (thinking) request failed: %s", e)
            raise RuntimeError(f"[DeepSeek Network Error] {e}") from e
