"""
HTTP-клиент для взаимодействия с FastAPI бэкендом AGMY-RAG.
"""
import logging
from typing import Any, Dict, Optional, Tuple, Union

from aiohttp import ClientSession

logger = logging.getLogger(__name__)


def build_url(base_url: str, path: str) -> str:
    """Построить полный URL из базового и пути."""
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


class APIClient:
    """Асинхронный HTTP-клиент для backend API."""

    def __init__(self, session: ClientSession, base_url: str):
        self._session = session
        self._base_url = base_url

    def _url(self, path: str) -> str:
        return build_url(self._base_url, path)

    async def _parse_response(self, resp) -> Any:
        """Распарсить ответ сервера (JSON или текст)."""
        ctype = resp.headers.get("Content-Type", "")
        if "application/json" in ctype:
            return await resp.json()
        return await resp.text()

    # ── Exam Themes ──────────────────────────────────────────────────────

    async def get_exam_themes(self, user_id: int) -> Tuple[bool, Optional[list], int, str]:
        """Получить список экзаменационных тем для пользователя."""
        url = self._url(f"/exams/themes/users/{user_id}")
        try:
            async with self._session.get(url) as resp:
                data = await self._parse_response(resp)
                if resp.status == 200:
                    return True, data if isinstance(data, list) else None, resp.status, ""
                return False, None, resp.status, str(data)
        except Exception as e:
            logger.error("API get_exam_themes failed: %s", e)
            return False, None, 0, str(e)

    # ── Exams ────────────────────────────────────────────────────────────

    async def create_exam(self, user_id: int, question_count: int,
                          exam_theme_id: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], int, str]:
        """Создать новую экзаменационную сессию."""
        url = self._url("/exams/")
        payload = {"user_id": user_id, "question_count": question_count}
        if exam_theme_id:
            payload["exam_theme_id"] = exam_theme_id
        try:
            async with self._session.post(url, json=payload) as resp:
                data = await self._parse_response(resp)
                if resp.status == 200:
                    return True, data if isinstance(data, dict) else None, resp.status, ""
                return False, data if isinstance(data, dict) else None, resp.status, str(data)
        except Exception as e:
            logger.error("API create_exam failed: %s", e)
            return False, None, 0, str(e)

    # ── Questions ────────────────────────────────────────────────────────

    async def ask_question(self, user_id: int) -> Tuple[bool, Optional[Dict[str, Any]], int, str]:
        """Запросить следующий вопрос для пользователя."""
        url = self._url(f"/exams/users/{user_id}/questions/ask/")
        try:
            async with self._session.post(url, json={}) as resp:
                data = await self._parse_response(resp)
                if resp.status == 200:
                    return True, data if isinstance(data, dict) else None, resp.status, ""
                return False, data if isinstance(data, dict) else None, resp.status, str(data)
        except Exception as e:
            logger.error("API ask_question failed: %s", e)
            return False, None, 0, str(e)

    async def get_unanswered_question(self, user_id: int) -> Tuple[bool, Optional[Dict[str, Any]], int, str]:
        """Получить неотвеченный вопрос для пользователя."""
        url = self._url(f"/exams/users/{user_id}/questions/unanswered/")
        try:
            async with self._session.get(url) as resp:
                data = await self._parse_response(resp)
                if resp.status == 200:
                    return True, data if isinstance(data, dict) else None, resp.status, ""
                return False, data if isinstance(data, dict) else None, resp.status, str(data)
        except Exception as e:
            logger.error("API get_unanswered_question failed: %s", e)
            return False, None, 0, str(e)

    async def get_questions(self, exam_id: Union[str, int]) -> Tuple[bool, Optional[Any], int, str]:
        """Получить список вопросов экзамена."""
        url = self._url(f"/exams/{exam_id}/questions/")
        try:
            async with self._session.get(url) as resp:
                data = await self._parse_response(resp)
                if resp.status == 200:
                    return True, data, resp.status, ""
                return False, data if isinstance(data, dict) else None, resp.status, str(data)
        except Exception as e:
            logger.error("API get_questions failed: %s", e)
            return False, None, 0, str(e)

    # ── Answers ──────────────────────────────────────────────────────────

    async def post_answer(self, user_id: int, answer_text: str) -> Tuple[bool, Optional[Dict[str, Any]], int, str]:
        """Отправить ответ на вопрос."""
        url = self._url("/answers/")
        payload = {"user_id": user_id, "answer_text": answer_text}
        try:
            async with self._session.post(url, json=payload) as resp:
                data = await self._parse_response(resp)
                if resp.status in (200, 201):
                    return True, data if isinstance(data, dict) else None, resp.status, ""
                return False, data if isinstance(data, dict) else None, resp.status, str(data)
        except Exception as e:
            logger.error("API post_answer failed: %s", e)
            return False, None, 0, str(e)

    # ── Stats ────────────────────────────────────────────────────────────

    async def get_stats_all(self, user_id: int) -> Tuple[bool, Optional[Any], int, str]:
        """Получить общую статистику пользователя."""
        url = self._url(f"/stats/users/{user_id}/all/")
        try:
            async with self._session.get(url) as resp:
                data = await self._parse_response(resp)
                if resp.status == 200:
                    return True, data, resp.status, ""
                return False, data if isinstance(data, dict) else None, resp.status, str(data)
        except Exception as e:
            logger.error("API get_stats_all failed: %s", e)
            return False, None, 0, str(e)

    async def get_stats_last(self, user_id: int) -> Tuple[bool, Optional[Any], int, str]:
        """Получить статистику последнего экзамена."""
        url = self._url(f"/stats/users/{user_id}/last/")
        try:
            async with self._session.get(url) as resp:
                data = await self._parse_response(resp)
                if resp.status == 200:
                    return True, data, resp.status, ""
                return False, data if isinstance(data, dict) else None, resp.status, str(data)
        except Exception as e:
            logger.error("API get_stats_last failed: %s", e)
            return False, None, 0, str(e)

    # ── Themes ───────────────────────────────────────────────────────────

    async def get_themes(self, user_id: int) -> Tuple[bool, Optional[list], int, str]:
        """Получить список тем теории для пользователя."""
        url = self._url(f"/themes/users/{user_id}/")
        try:
            async with self._session.get(url) as resp:
                data = await self._parse_response(resp)
                if resp.status == 200:
                    return True, data if isinstance(data, list) else None, resp.status, ""
                return False, None, resp.status, str(data)
        except Exception as e:
            logger.error("API get_themes failed: %s", e)
            return False, None, 0, str(e)

    async def get_theme_file(self, theme_id: str) -> Tuple[bool, Optional[bytes], str, str, int, str]:
        """Получить файл темы."""
        url = self._url(f"/themes/{theme_id}/file/")
        try:
            async with self._session.get(url) as resp:
                filename = resp.headers.get("Content-Disposition", "").split("filename=")[-1].strip(
                    '"') if "filename=" in resp.headers.get("Content-Disposition", "") else "file.pdf"
                ctype = resp.headers.get("Content-Type", "")
                if resp.status == 200:
                    file_bytes = await resp.read()
                    return True, file_bytes, filename, ctype, resp.status, ""
                data = await resp.text()
                return False, None, "", ctype, resp.status, data
        except Exception as e:
            logger.error("API get_theme_file failed: %s", e)
            return False, None, "", "", 0, str(e)
