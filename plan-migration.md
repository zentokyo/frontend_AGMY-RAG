# AGMY RAG — План миграции на веб + DeepSeek V4 Flash + Qdrant

## Контекст

Монорепозиторий медицинской образовательной платформы (Астраханский ГМУ).
Происходит **полная миграция с Telegram-бота на веб-интерфейс**.
Telegram-бот (`bot/`) и Python FastAPI-бэкенд (`backend/`) — устаревшие компоненты,
весь функционал переносится в Node.js API (`apps/api/`) + React-фронтенд (`apps/chat-frontend/`).

## Целевая архитектура

```
                    ┌─────────────────────────┐
                    │   chat-frontend (React)  │
                    │  /api/app/*              │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  Node.js API (Express)  │ ← единый сервис
                    │  PostgreSQL + JWT       │
                    └────┬─────┬──────┬──────┘
                         │     │      │
              ┌──────────┘     │      └──────────┐
              ▼                ▼                  ▼
   ┌──────────────────┐ ┌────────────┐ ┌──────────────────┐
   │ DeepSeek V4 Flash│ │ GigaChat   │ │     Qdrant       │
   │  (REST API)      │ │ Embeddings │ │  (векторная БД)  │
   │  LLM для оценки  │ │ (REST API) │ │  self-hosted     │
   │  и ментора       │ │ векториз.  │ │  Docker          │
   └──────────────────┘ └────────────┘ └──────────────────┘
                          
              ┌──────────────────────────────────────┐
              │ Python (только для ingest документов) │
              │ загрузка → split → embed → Qdrant     │
              │ можно заменить Node.js позже           │
              └──────────────────────────────────────┘
```

**Ключевое отличие от ChromaDB:** Qdrant имеет полноценный REST API и
официальный Node.js-клиент (`@qdrant/js-client-rest`). Это позволяет:
- Убрать Python из горячего пути (поиск + оценка ответов — чистый Node.js)
- Оставить Python только для разовой операции инжеста документов
- Упростить инфраструктуру: Qdrant как ещё один Docker-контейнер

---

## Этапы

### Шаг 1 — DeepSeek V4 Flash клиент + GigaChat Embeddings (Python)

Создать `backend/src/core/rag/deepseek_llm.py` — класс `DeepSeekFlashLLM`,
OpenAI-совместимый HTTP-клиент для DeepSeek V4 Flash API.

- Вызов через `requests` (как сейчас GigaChat)
- Конфигурация через переменные окружения: `DEEPSEEK_API_KEY`, `DEEPSEEK_API_URL`
- Заменить `GigaChatLiteLLM` на `DeepSeekFlashLLM` во всех функциях `main.py`
- GigaChatEmbeddings **пока остаётся** — нужен и для инжеста, и для векторизации запросов
- Добавить `thinking: true` в параметры вызова DeepSeek для режима High Thinking

**Критерий успеха:** Python-функция `answer_question()` вызывает DeepSeek вместо GigaChat.

### Шаг 2 — Поднять Qdrant и перенести данные

**Docker (`docker-compose.yml`):**
- Добавить сервис `assistant-vector-db` (Qdrant, порт 6333)
- Добавить healthcheck
- Прокинуть volume для persistence

**Node.js — Qdrant-клиент (`apps/api/src/services/qdrant.js`):**
- Подключение через `@qdrant/js-client-rest`
- Конфигурация через `QDRANT_URL` (по умолч. `http://localhost:6333`)
- Функции: `upsertPoints()`, `searchPoints()`, `deletePoints()`
- Имя коллекции: `assistant_knowledge`

**Python — ingest под Qdrant (`backend/src/core/rag/ingest_qdrant.py`):**
- Загружает документы → сплитит (как сейчас) → эмбеддинг через GigaChat
- Сохраняет векторы в Qdrant через REST API
- Добавляет метаданные: source, source_theme, content_hash

**Перенос существующих данных:**
- Прочитать все документы из ChromaDB (`db_metadata_v5`)
- Заново прогнать через ingest → Qdrant
- После верификации ChromaDB можно удалить

**Критерий успеха:** Qdrant запущен, данные перенесены, `curl` поиск возвращает релевантные чанки.

### Шаг 3 — Node.js RAG-сервис (вместо Python)

Создать `apps/api/src/services/rag.js` — полностью на Node.js:

- **Векторизация запроса:** вызов GigaChat Embeddings API через `fetch`/`axios`
- **Поиск в Qdrant:** `searchPoints()` с вектором запроса, фильтрация по `source_theme`
- **Формирование контекста:** сбор чанков, ограничение по `MAX_CONTEXT_CHARS`
- **Вызов DeepSeek:** отправка промпта с контекстом + вопрос + ответ студента
- **Возврат:** `{ is_correct: boolean, confidence: number }`

**Варианты проверки ответа:**
- **Strict mode:** точное сравнение (как сейчас) — fallback
- **RAG mode:** DeepSeek оценивает ответ по контексту из Qdrant
- **Hybrid:** RAG-оценка + если None → точное сравнение

**Критерий успеха:** `rag.js` из Node.js возвращает корректную оценку без вызова Python.

### Шаг 4 — Подключить RAG к endpoint'у ответов

Изменить `apps/api/src/routes/app/answers.js`:

- Вызывать `rag.js` вместо `normalizedGiven === normalizedModel`
- Пробросить `theme_title` из экзамена для фильтрации поиска
- Если RAG недоступен — fallback на точное сравнение

Параллельно:
- Удалить `backend/src/core/rag/evaluate.py` (больше не нужен, т.к. RAG в Node.js)
- Обновить `services/python.js` — убрать evaluate, оставить только ingest

**Критерий успеха:** `POST /api/app/answers` проверяет ответ через DeepSeek + Qdrant.

### Шаг 5 — End-to-end тест

- Поднять Docker Compose с Qdrant
- Накатить миграции и seed
- Прогнать ingest в Qdrant
- Пройти полный цикл: регистрация → курс → тема → экзамен → RAG-оценка → результат

**Критерий успеха:** Полный user flow работает на новом стеке.

### Шаг 6 — AI-ментор (чат с ассистентом по RAG)

После неудачной попытки экзамена студенту предлагается:
1. Повторить материал темы
2. Задать вопрос ассистенту (DeepSeek V4 Flash + RAG по Qdrant)

**Node.js — `POST /api/app/mentor/ask`:**

- Принимает `{ question: string, theme_title?: string, conversation_history?: array }`
- Векторизует вопрос через GigaChat Embeddings
- Ищет релевантные чанки в Qdrant
- Формирует промпт: контекст + история диалога + вопрос
- Вызывает DeepSeek V4 Flash с `thinking: true`
- Возвращает `{ answer: string, sources: [...], thinking?: string }`

**Frontend — компонент MentorChat:**

- Чат-интерфейс (поле ввода + история)
- Отображается:
  - После провала экзамена — две кнопки: "Повторить материал" (теория), "Спросить ассистента" (чат)
  - Как отдельная страница `/app/mentor`
- Индикатор "думает..." пока DeepSeek обрабатывает (High Thinking может быть долгим)
- Сообщения хранятся в состоянии (Zustand) или в БД (опционально)

**Критерий успеха:** Студент может задать вопрос по теме, получить ответ с контекстом из базы знаний.

### Шаг 7 — Теория (скачивание файлов)

Реализовать `GET /api/app/themes/:id/download` — стриминг ZIP-архива из MinIO.

Сейчас — заглушка, возвращает метаданные.

**Критерий успеха:** Студент может скачать файлы теории по теме.

### Шаг 8 — Чистка

- Удалить `bot/` из репозитория
- Убрать `assistant_backend` из `docker-compose.yml`
- Удалить `backend/src/core/rag/db_metadata_v5` (ChromaDB, заменена Qdrant)
- Удалить `backend/src/core/rag/gigachat_auth.py` (если GigaChat остался только как эмбеддинг)
- Убрать `EXAM_API_BASE_URL`, `BOT_TOKEN`, `GIGACHAT_AUTHORIZATION_KEY` (если не нужны)
- Обновить README

**Критерий успеха:** Проект чист от устаревших компонентов.

---

## Архитектурные решения

| Решение | Обоснование |
|---------|-------------|
| Qdrant вместо ChromaDB | REST API, Node.js-клиент, self-hosted Docker, не привязан к Python |
| RAG на Node.js (горячий путь) | 0 вызовов Python при оценке ответа — меньше latency, проще деплой |
| Python только для ingest | Инжест — редкая операция, портировать на Node.js дорого прямо сейчас |
| GigaChat Embeddings остаются | DeepSeek не предоставляет embeddings API. Qdrant можно перестроить с другой моделью позже |
| GigaChat Auth остаётся | Только для embeddings, LLM заменён на DeepSeek |

## Ограничения

- DeepSeek V4 Flash API требует ключ (будет передан позже)
- GigaChat Embeddings требуют `GIGACHAT_AUTHORIZATION_KEY`
- Qdrant — ещё один Docker-контейнер (но лёгкий)
- High Thinking режим DeepSeek может быть медленным (10-30 сек) — нужен UI-индикатор
