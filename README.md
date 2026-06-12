# AGMY RAG

Медицинская образовательная платформа с единым Python backend:

- FastAPI обслуживает admin и app API, auth, курс, экзамены и RAG;
- PostgreSQL хранит пользователей, учебную структуру и результаты;
- MinIO хранит документы;
- Qdrant хранит векторы базы знаний;
- GigaChat `EmbeddingsGigaR` создаёт эмбеддинги;
- DeepSeek оценивает ответы;
- React/Vite используются для admin и пользовательского frontend.

Node.js больше не используется как backend. Он нужен только как build/dev tool
для React-приложений. Production-сборка admin frontend включается в образ
FastAPI и раздаётся с того же origin.

## Структура

| Каталог | Назначение |
|---|---|
| `backend/` | FastAPI, доменная логика, Alembic, Qdrant и RAG |
| `apps/admin-frontend/` | Административная панель |
| `apps/chat-frontend/` | Пользовательский кабинет |
| `tests/api/` | Интеграционные тесты публичного FastAPI API |
| `python/` | Вспомогательные Python-утилиты |
| `converters/` | Конвертеры и legacy Telegram-бот |
| `theme_files/` | Начальные документы для MinIO |

## Быстрый запуск

Создайте окружение:

```bash
cp .env.example .env
```

Соберите admin frontend и запустите инфраструктуру с backend:

```bash
npm run build
docker compose up -d --build --remove-orphans assistant-vector-db assistant_db assistant-file-storage create-buckets assistant_backend
```

После запуска:

- admin frontend: [http://127.0.0.1:8001](http://127.0.0.1:8001);
- FastAPI docs: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs);
- Qdrant: [http://127.0.0.1:6333](http://127.0.0.1:6333);
- MinIO console: [http://127.0.0.1:9001](http://127.0.0.1:9001).

При старте `assistant_backend` автоматически запускает Python migration runner.
Он поддерживает как чистую базу, так и существующую legacy-схему без таблицы
`alembic_version`.

Создать или обновить первого администратора:

```bash
npm run db:seed
```

По умолчанию используются `SEED_ADMIN_EMAIL` и `SEED_ADMIN_PASSWORD` из `.env`.

## Frontend-разработка

Сначала поднимите FastAPI на `http://127.0.0.1:8001`, затем:

```bash
npm run dev
```

Адреса:

- admin: [http://127.0.0.1:5173](http://127.0.0.1:5173);
- пользовательский кабинет: [http://127.0.0.1:5174](http://127.0.0.1:5174).

Оба Vite-сервера проксируют `/api` прямо в FastAPI.

## Windows

- Используйте адреса `127.0.0.1`, а не `localhost`: так Docker Desktop,
  браузер и Vite не упираются в IPv6/DNS-разницу Windows.
- Если PowerShell показывает русский текст кракозябрами, включите UTF-8:
  `chcp 65001`.
- Репозиторий фиксирует UTF-8 и LF через `.editorconfig` и `.gitattributes`;
  в VS Code проверьте `File Encoding: UTF-8`.

Запуск отдельно:

```bash
npm run dev:admin
npm run dev:chat
```

Production-сборки:

```bash
npm run build
npm run build:chat
```

Admin build создаётся в `apps/admin-frontend/dist`. Во время Docker build он
копируется в `/app/static/admin` внутри FastAPI-образа.

## Миграции

Через Docker:

```bash
npm run db:migrate
```

Локально:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.cli.migrate
python -m src.cli.seed_admin
```

Обычный Alembic также доступен после первичного принятия legacy-схемы:

```bash
cd backend
alembic upgrade head
```

## Индексация базы знаний

Загрузка файлов через админку сохраняет документы в MinIO ограниченно
параллельно (`RAG_UPLOAD_STORAGE_CONCURRENCY`) и ставит файлы в очередь
`ingest_job`. Отдельный сервис `assistant_ingest_worker` забирает задачи из
PostgreSQL через `FOR UPDATE SKIP LOCKED` и индексирует их с ограничением
`RAG_UPLOAD_INDEX_CONCURRENCY`. Статусы видны в списке файлов:
`queued` → `indexing` → `indexed` или `failed`. При перезапуске backend
задачи остаются в очереди, а зависшие `running` worker возвращает в `queued`
после `RAG_INGEST_STALE_AFTER_SECONDS`. После `RAG_INGEST_MAX_ATTEMPTS`
следующая попытка переводит файл/job в `dead_letter`, чтобы проблемный документ
не зацикливал переиндексацию.

Каждый запуск индексации сохраняется в `ingest_job`: там лежат тип задачи,
попытка, стадия (`reading`, `extracting`, `chunking`, `embedding`,
`qdrant_upsert`, `done`), процент прогресса, ошибка и JSON-отчет по extraction /
chunking. В админке доступны повторная индексация одного файла, всей темы и всех
failed-файлов.

Для ручного запуска worker одной пачкой:

```bash
python -m src.cli.ingest_worker --once --batch-size 2
```

В админке у каждого файла доступна история job: попытки, стадии, ошибки, время
старта/финиша, тайминги стадий (`reading`, `extracting`, `chunking`,
`qdrant_delete`, `embedding_qdrant_upsert`) и JSON-отчет extraction/chunking.
Там же доступна панель мониторинга worker: глубина очереди, running/paused,
failed/dead-letter, средняя длительность job и средние stage timings.

Индексацию файла можно поставить на паузу, возобновить или отменить. Для
`queued` job действие применяется сразу, для `running` job worker выполняет его
кооперативно между стадиями, чтобы не оставить Qdrant/SQL в промежуточном
состоянии.

Для рабочей админской базы используйте файлы, привязанные к темам в SQL:

```bash
python -m src.cli.reindex_admin_documents --blue-green --concurrency 2
```

Флаг `--blue-green` собирает новую staging-коллекцию Qdrant и публикует ее
через alias `QDRANT_COLLECTION` только после успешной индексации всех файлов.
`--recreate-qdrant` оставлен для локальных разрушительных пересборок коллекции.

Проверка извлечения текста и чанкинга без внешнего embeddings API и без записи в
Qdrant:

```bash
python -m src.cli.reindex_admin_documents --dry-run --concurrency 2
```

Быстрая проверка retrieval по реальным вопросам из SQL:

```bash
python -m src.cli.rag_retrieval_smoke --limit 18 --k 5 --verbose
```

Проверка использует тот же retrieval-слой, что и приложение: Qdrant забирает
расширенный пул кандидатов (`RAG_RETRIEVAL_FETCH_K`), после чего включает
гибридный rerank по vector score + lexical overlap и MMR-диверсификацию.
При оценке ответа в LLM передается ограниченный контекст
(`RAG_MAX_CONTEXT_CHARS`, по умолчанию `8000` символов).
Для регулярной оценки качества можно сохранять JSON-отчет с вопросами,
попаданиями и top-k чанками:

```bash
python -m src.cli.rag_retrieval_smoke \
  --limit 0 \
  --k 5 \
  --fetch-k 30 \
  --min-filtered-hit-rate 1.0 \
  --min-unfiltered-topk-theme-rate 0.95 \
  --output-json retrieval-smoke-report.json
```

Проверка полного RAG/LLM-оценивания ответов по SQL `answer_text`:

```bash
python -m src.cli.rag_answer_eval \
  --limit 0 \
  --min-positive-pass-rate 0.8 \
  --max-unknown-rate 0.2 \
  --output-json answer-eval-report.json
```

Legacy-команда `python -m src.core.rag.ingest` читает Markdown из `KB_PATH` и нужна
только для старого локального набора знаний. Не используйте ее для проверки
админских тем и файлов из дампа.

## Проверки

```bash
npm run test:api
npm run test:retrieval
npm run test:answers
npm run build
npm run build:chat
npm run test:e2e
```

Быстрый набор без browser e2e:

```bash
npm run test:all
```

## Основные переменные

- `POSTGRES_*` — PostgreSQL;
- `S3_*` — MinIO;
- `QDRANT_URL`, `QDRANT_COLLECTION`, `QDRANT_VECTOR_SIZE` — Qdrant;
- `RAG_RETRIEVAL_FETCH_K`, `RAG_HYBRID_RERANK_*`, `RAG_MMR_*` — качество retrieval;
- `GIGACHAT_AUTHORIZATION_KEY`, `GIGACHAT_EMBEDDINGS_MODEL` — эмбеддинги;
- `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` — LLM;
- `JWT_SECRET`, `JWT_REFRESH_SECRET` — web auth;
- `COOKIE_SECURE=true` — secure refresh cookies в HTTPS production;
- `CLIENT_ORIGIN` — разрешённые Vite origins;
- `FASTAPI_PUBLISHED_PORT` — внешний порт FastAPI, по умолчанию `8001`.

## Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, asyncpg, Alembic, Dishka |
| Admin | React 19, Vite, Tailwind, Zustand, TanStack Query |
| App | React 19, Vite, Tailwind, Zustand, TanStack Query |
| Data | PostgreSQL, MinIO, Qdrant |
| AI | GigaChat EmbeddingsGigaR, DeepSeek |
