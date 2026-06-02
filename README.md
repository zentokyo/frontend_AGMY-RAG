# AGMY RAG — монорепозиторий

Проект состоит из нескольких частей, которые можно запускать отдельно:

- **контейнеры инфраструктуры**: PostgreSQL, MinIO, Qdrant;
- **Node.js API**: auth, документы, вопросы, курс, экзамены, RAG-оценка;
- **веб-админка**: React + Vite, порт `5173`;
- **веб-чат / личный кабинет**: React + Vite, порт `5174`;
- **Python FastAPI backend**: legacy-сервис ассистента, порт `8000`;
- **RAG-утилиты**: индексация базы знаний и интеграции с Qdrant/LLM.

> Важно: старый Telegram-бот хранится в `converters/bot` и остаётся legacy-сервисом. Основной пользовательский сценарий сейчас живёт в веб-чате `apps/chat-frontend`.

## Структура

| Каталог | Назначение |
|--------|------------|
| `apps/api/` | Основной Node.js API: auth, документы, вопросы, `/api/app/*`, курс, RAG |
| `apps/admin-frontend/` | Админ-панель: React 19, Vite, Tailwind |
| `apps/chat-frontend/` | Веб-чат / личный кабинет студента: React 19, Vite, Tailwind |
| `backend/` | Legacy FastAPI, Alembic, доменная логика, RAG-утилиты |
| `backend/knowledge_base/` | База знаний для RAG |
| `python/` | `admin_tools.py` и вспомогательные Python-утилиты для админ API |
| `converters/` | Вспомогательные конвертеры и перенесённые исходники старого бота |
| `theme_files/` | Стартовые PDF для загрузки в MinIO |
| `dump.sql` | Дамп начальных данных БД `assistant` |

Подробнее по Python-бэкенду см. `backend/readme.md`.

## Требования

- Node.js 20+ и npm.
- Docker Desktop / OrbStack / Colima с рабочим `docker compose`, если запускаете контейнеры.
- PostgreSQL, MinIO и Qdrant: через Docker или уже поднятые локально.
- Python 3.12 для локального запуска legacy FastAPI/RAG-утилит.

## Переменные окружения

Создайте корневой `.env`:

```bash
cp .env.example .env
```

Проверьте минимум:

- `POSTGRES_*` — доступ к базе `assistant`;
- `S3_*` — MinIO / S3;
- `QDRANT_URL` и `QDRANT_COLLECTION` — векторная БД;
- `DEEPSEEK_API_KEY` — LLM для RAG-оценки ответов;
- `GIGACHAT_AUTHORIZATION_KEY` — эмбеддинги RAG;
- `JWT_SECRET` и `JWT_REFRESH_SECRET` — секреты Node API;
- `CLIENT_ORIGIN` — должен включать `http://localhost:5173` и `http://localhost:5174` для dev-фронтов.

`apps/api/src/env.js` сначала читает корневой `.env`, затем `apps/api/.env`. Значения из `apps/api/.env` перекрывают корневые, поэтому для локальной разработки удобно держать там:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=assistant
DB_USER=postgres
DB_PASSWORD=example
CLIENT_ORIGIN=http://localhost:5173,http://localhost:5174,http://localhost:3001
```

MinIO по умолчанию слушает `9000`. Если этот порт занят, поменяйте в `.env` `S3_PORT`, например:

```env
S3_PORT=9002
S3_ENDPOINT=http://localhost:9002
```

## 1. Контейнеры инфраструктуры

Запуск только базовых контейнеров:

```bash
docker compose up -d assistant-vector-db assistant_db assistant-file-storage create-buckets
```

Проверка:

```bash
docker compose ps
curl http://localhost:6333/healthz
curl http://localhost:${S3_PORT:-9000}/minio/health/live
```

Первичная загрузка дампа БД, если volume пустой:

```bash
docker exec -i assistant_db psql -U postgres -d assistant < ./dump.sql
```

Миграции и seed для Node API выполняйте после установки npm-зависимостей из следующего раздела:

```bash
npm run db:migrate
npm run db:seed
```

## 2. Node.js API

Установка зависимостей:

```bash
npm run install:all
```

Локальный dev-запуск API:

```bash
npm run dev:api
```

API будет доступен на [http://localhost:3001](http://localhost:3001).

Быстрая проверка:

```bash
curl -i http://localhost:3001/api/auth/me
```

Без токена корректный ответ — `401` с `Missing token`.

## 3. Веб-админка

Админка в dev-режиме запускается отдельно от API:

```bash
npm run dev:admin
```

Откройте [http://localhost:5173](http://localhost:5173).

Vite проксирует запросы `/api` на `http://localhost:3001`, поэтому перед работой с админкой должен быть запущен Node API.

Production-сборка админки:

```bash
npm run build
```

Сборка кладётся в `apps/api/public` и может отдаваться Express-сервером на `http://localhost:3001`.

## 4. Веб-чат / личный кабинет

Чат в dev-режиме:

```bash
npm run dev:chat
```

Откройте [http://localhost:5174](http://localhost:5174).

Как и админка, чат проксирует `/api` на `http://localhost:3001`; Node API должен быть запущен заранее.

Production-сборка чата:

```bash
npm run build:chat
```

## 5. Всё веб-приложение локально

Если инфраструктура уже поднята, можно одновременно запустить API, админку и чат:

```bash
npm run dev
```

Будут доступны:

- API: [http://localhost:3001](http://localhost:3001)
- Admin: [http://localhost:5173](http://localhost:5173)
- Chat: [http://localhost:5174](http://localhost:5174)

## 6. Docker-запуск API + собранной админки

Если нужна контейнерная версия Node API со статикой админки, запускайте сервисы явно:

```bash
docker compose up -d --build assistant-vector-db assistant_db assistant-file-storage create-buckets assistant_backend admin-server
```

Откройте [http://localhost:3001](http://localhost:3001).

Эта команда не запускает `assistant_bot` и не поднимает dev-сервер чата. Чат для разработки запускайте отдельно через `npm run dev:chat`.

Полный Docker-запуск с legacy-ботом:

```bash
docker compose up -d --build
```

## 7. Docker dev-фронты

Если хотите поднять Vite-фронты тоже в Docker, запускайте профиль `dev` с явным списком сервисов:

```bash
docker compose --profile dev up -d --build assistant-vector-db assistant_db assistant-file-storage create-buckets assistant_backend admin-server admin-client-dev chat-client-dev
```

После запуска:

- Admin: [http://localhost:5173](http://localhost:5173)
- Chat: [http://localhost:5174](http://localhost:5174)
- API: [http://localhost:3001](http://localhost:3001)

## 8. Python FastAPI backend

Локальный запуск legacy FastAPI:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn --factory src.main:create_app --host 0.0.0.0 --port 8000
```

Документация FastAPI: [http://localhost:8000/docs](http://localhost:8000/docs).

Миграции Python-бэкенда:

```bash
cd backend
alembic upgrade head
```

База должна совпадать с той, что использует Node API (`assistant`).

## Проверки

Сборки:

```bash
npm run build
npm run build:chat
```

API-тесты:

```bash
npm run test:api
```

E2E пользовательского кабинета:

```bash
npm run test:e2e
```

Полный быстрый набор без e2e:

```bash
npm run test:all
```

## Частые проблемы

**Docker не стартует / нет socket**

Запустите Docker Desktop, OrbStack или Colima и повторите `docker compose ps`.

**MinIO не стартует на `9000`**

Поменяйте `S3_PORT` в `.env`, например на `9002`, и обновите локальный `S3_ENDPOINT`.

**RAG падает в fallback**

Проверьте, что запущен Qdrant, заполнена коллекция `QDRANT_COLLECTION`, указаны `DEEPSEEK_API_KEY` и `GIGACHAT_AUTHORIZATION_KEY`.

## Стек

| Слой | Технологии |
|------|------------|
| API | Node 20, Express, PostgreSQL, JWT, S3/MinIO, Qdrant |
| Admin | React 19, Vite, Tailwind, Zustand, TanStack Query, axios |
| Chat | React 19, Vite, Tailwind, Zustand, TanStack Query, axios |
| Legacy backend | Python 3.12, FastAPI, asyncpg, MinIO |
| RAG | Qdrant, GigaChat embeddings, DeepSeek |
