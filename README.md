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
docker compose up -d --build --remove-orphans \
  assistant-vector-db \
  assistant_db \
  assistant-file-storage \
  create-buckets \
  assistant_backend
```

После запуска:

- admin frontend: [http://localhost:8001](http://localhost:8001);
- FastAPI docs: [http://localhost:8001/docs](http://localhost:8001/docs);
- Qdrant: [http://localhost:6333](http://localhost:6333);
- MinIO console: [http://localhost:9001](http://localhost:9001).

При старте `assistant_backend` автоматически запускает Python migration runner.
Он поддерживает как чистую базу, так и существующую legacy-схему без таблицы
`alembic_version`.

Создать или обновить первого администратора:

```bash
npm run db:seed
```

По умолчанию используются `SEED_ADMIN_EMAIL` и `SEED_ADMIN_PASSWORD` из `.env`.

## Frontend-разработка

Сначала поднимите FastAPI на `http://localhost:8001`, затем:

```bash
npm run dev
```

Адреса:

- admin: [http://localhost:5173](http://localhost:5173);
- пользовательский кабинет: [http://localhost:5174](http://localhost:5174).

Оба Vite-сервера проксируют `/api` прямо в FastAPI.

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

## Проверки

```bash
npm run test:api
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
