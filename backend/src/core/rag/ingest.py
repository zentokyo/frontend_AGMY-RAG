import hashlib
import os
import shutil
import re
import requests
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

# ИСПРАВЛЕННЫЙ ИМПОРТ (убедитесь, что файл называется gigachat_auth.py)
try:
    from src.core.rag.gigachat_auth import get_gigachat_token, GigaChatAuthError
except ImportError:
    # Если запуск идет из корня или папки rag, пробуем относительный импорт
    from gigachat_auth import get_gigachat_token, GigaChatAuthError

load_dotenv()

CHROMA_PATH = "src/core/rag/db_metadata_v5"  # Путь должен совпадать с основным файлом
DATA_PATH = "knowledge_base"
global_unique_hashes = set()


class GigaChatEmbeddings:
    def __init__(self):
        # Мы не сохраняем токен в self.token здесь,
        # чтобы он обновлялся через get_gigachat_token() автоматически
        self.api_url = "https://gigachat.devices.sberbank.ru/api/v1/embeddings"

    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_gigachat_token()}"
        }

    def embed_query(self, text: str):
        payload = {"model": "Embeddings", "input": text}
        response = requests.post(self.api_url, headers=self._get_headers(), json=payload, verify=False)
        if response.status_code != 200:
            raise RuntimeError(f"GigaChat Error: {response.text}")
        return response.json()["data"][0]["embedding"]

    def embed_documents(self, texts: list[str], batch_size: int = 8):
        all_embeddings = []
        # GigaChat имеет лимит на длину текста в одном эмбеддинге (~2000-4000 токенов)
        # Ваш RecursiveCharacterTextSplitter уже делает чанки по 450, так что доп. разбивка не нужна

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload = {"model": "Embeddings", "input": batch}
            # Перед каждым батчем get_gigachat_token() проверит, не истек ли старый токен
            response = requests.post(self.api_url, headers=self._get_headers(), json=payload, verify=False)

            if response.status_code != 200:
                raise RuntimeError(f"GigaChat Error: {response.text}")
            all_embeddings.extend([item["embedding"] for item in response.json()["data"]])

        return all_embeddings


# ... (остальные функции load_documents, split_text остаются без изменений) ...

def save_to_chroma(chunks: list[Document]):
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
    os.makedirs(os.path.dirname(CHROMA_PATH), exist_ok=True)

    try:
        # Используем обновленный класс
        embedding_function = GigaChatEmbeddings()
        db = Chroma.from_documents(
            documents=chunks,
            embedding=embedding_function,
            persist_directory=CHROMA_PATH,
            collection_metadata={"hnsw:space": "cosine"}
        )
        print(f"[SUCCESS] Сохранено {len(chunks)} чанков в {CHROMA_PATH}")
    except Exception as e:
        print(f"[ERROR] Ошибка Chroma: {e}")
        raise


if __name__ == "__main__":
    generate_data_store()
