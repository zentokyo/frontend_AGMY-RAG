# AGMY RAG — монорепозиторий

Единый проект: **ассистент на FastAPI**, **Telegram-бот**, **админ-панель** (React + Node.js), общая **PostgreSQL** и **MinIO**, утилиты **RAG/Chroma** в каталоге `backend/`.

## Структура

| Каталог | Назначение |
|--------|------------|
| `backend/` | FastAPI, доменная логика, Alembic-миграции, RAG (`src/core/rag/`), при необходимости файлы в `knowledge_base/` |
| `bot/` | Telegram-бот (`python-telegram-bot`), обращается к `EXAM_API_BASE_URL` |
| `apps/admin-frontend/` | Админ-панель: React 19, Vite, Tailwind |
| `apps/chat-frontend/` | Основной веб-чат/кабинет: React 19, Vite, Tailwind |
| `apps/api/` | Основной Node.js API: auth, документы, вопросы, миграция на `/api/app/*` |
| `python/` | `admin_tools.py` — обслуживание Chroma (используется при расширении админ API) |
| `converters/` | Вспомогательные конвертеры из исходного проекта |
| `theme_files/` | Стартовые PDF для загрузки в MinIO (сервис `create-buckets`) |
| `dump.sql` | Дамп начальных данных БД `assistant` |

Подробнее по Python-бэкенду см. `backend/readme.md`.

---

## Быстрый старт (Docker — всё сразу)

1. **Переменные окружения**

   ```bash
   cp .env.example .env
   ```

   Заполните как минимум `GIGACHAT_AUTHORIZATION_KEY`, `BOT_TOKEN`. Остальное можно оставить как в примере для локальной разработки.

2. **Запуск контейнеров**

   ```bash
   docker compose up -d --build
   ```

   Поднимутся: `assistant_db` (Postgres), `assistant-file-storage` (MinIO), `assistant_backend` (FastAPI, порт **8000**), `assistant_bot`, `create-buckets`, `admin-server` (API + собранная админка, порт **3001**).

3. **Импорт дампа БД** (первый раз или после чистого volume):

   ```bash
   docker exec -i assistant_db psql -U postgres -d assistant < ./dump.sql
   ```

   На Windows при необходимости:

   ```bat
   docker exec -i assistant_db psql -U postgres -d assistant < dump.sql
   ```

4. **Миграции и таблицы админки** (`admin_users`, refresh-токены):

   ```bash
   docker compose exec admin-server node src/db/migrate.js
   docker compose exec admin-server node src/db/seed.js
   ```

5. **Открыть в браузере**

   - Админ-панель: [http://localhost:3001](http://localhost:3001) (логин из `SEED_ADMIN_*` в `.env`).
   - API ассистента: [http://localhost:8000/docs](http://localhost:8000/docs) (если включён OpenAPI).

**Опционально — дев-сервер Vite (горячая перезагрузка фронта):**

```bash
docker compose --profile dev up -d --build
```

Фронты: [http://localhost:5173](http://localhost:5173) (admin) и [http://localhost:5174](http://localhost:5174) (chat), прокси на API настроены в `apps/admin-frontend/vite.config.js` и `apps/chat-frontend/vite.config.js`.

---

## Локальная разработка без Docker (только админка + свой Postgres)

1. Поднимите Postgres и MinIO (или возьмите уже запущенные из `docker compose up assistant_db assistant-file-storage`).
2. `cp .env.example .env` в **корне** и при необходимости создайте `apps/api/.env` с `DB_HOST=localhost` и паролями.
3. Установка и запуск:

   ```bash
   npm run install:all
   npm run db:migrate
   npm run db:seed
   npm run dev
   ```

   Будут: API [http://localhost:3001](http://localhost:3001), admin [http://localhost:5173](http://localhost:5173), chat [http://localhost:5174](http://localhost:5174).

4. Бэкенд FastAPI и бота при этом запускайте отдельно из `backend/` и `bot/` по их `readme`/Dockerfile при необходимости.

---

## Миграции Python-бэкенда (Alembic)

Из каталога `backend/` с установленными зависимостями и настроенным `.env` (см. `backend/.env.example`):

```bash
cd backend
alembic upgrade head
```

База должна совпадать с той, что использует Node-админка (`assistant`).

---

## Полезные переменные

| Назначение | Файл / ключи |
|------------|----------------|
| Docker Compose | Корневой `.env` (шаблон — `.env.example`) |
| Node загружает | сначала корневой `.env`, затем `apps/api/.env` (перекрывает) |
| JWT, CORS, S3 для админки | `JWT_*`, `CLIENT_ORIGIN`, `S3_*`, `STORAGE_TYPE` |
| Telegram / FastAPI | `BOT_TOKEN`, `EXAM_API_BASE_URL`, `POSTGRES_*`, `S3_*`, `GIGACHAT_AUTHORIZATION_KEY` |

Пути к `ingest.py` и Chroma для админ-сервера в Docker заданы в `docker-compose.yml` (`BACKEND_ROOT`, `INGEST_*`). Вызов Python из образа `node:alpine` для полного пайплайна RAG может требовать установленного Python на хосте или доработки образа — при необходимости запускайте индексацию из окружения `backend/`.

---

## Сборка production-образа админки (только Node + статика)

Корневой `Dockerfile` собирает `apps/admin-frontend` в `apps/api/public` и запускает Express из `apps/api`. Используется сервисом `admin-server` в Compose.

---

## Стек (кратко)

| Слой | Технологии |
|------|------------|
| Ассистент | Python 3.12, FastAPI, asyncpg, MinIO, GigaChat |
| Бот | python-telegram-bot, aiohttp |
| Админка | React 19, Vite, Tailwind, Zustand, TanStack Query, axios |
| Админ API | Node 20, Express, PostgreSQL, JWT + httpOnly refresh |
