# AGMY RAG — текущий план миграции

Статус на 2026-06-08: миграция backend с Node/Express на Python/FastAPI
завершена для активного продукта.

## Что уже сделано

- Единый backend: `backend/` на FastAPI.
- Admin API, public app API, auth, documents, questions, course lifecycle,
  exams, answers, stats и RAG живут в Python.
- Qdrant используется как основная векторная БД для RAG.
- Admin SPA собирается Vite и отдаётся FastAPI из `backend/static/admin`.
- Пользовательский frontend работает напрямую с FastAPI через `/api/app/*`.
- Старый Node backend удалён из репозитория и из `docker-compose.yml`.

## Текущая схема

```text
apps/admin-frontend ── build ─┐
                              ├── backend/FastAPI ── PostgreSQL
apps/chat-frontend ───────────┤                 ├── Qdrant
                              │                 └── MinIO
                              └── static/admin SPA
```

Node.js остаётся только как tooling для frontend-разработки и сборки Vite.
Node runtime больше не участвует в backend path.

## Ближайшие спокойные шаги

1. Улучшать качество RAG в Python: chunking, reranking, фильтрация по теме,
   оценка ответа не как простая Q&A, а как учебный экзаменационный сценарий.
2. Довести ingest и reindex pipeline под Qdrant до удобной CLI/admin-операции.
3. Убрать или перенести оставшиеся архивные директории, которые не участвуют
   в запуске продукта.
4. Расширить e2e-покрытие: admin documents upload, course final exam,
   негативные сценарии авторизации и прав доступа.

## Проверка

Актуальные базовые команды:

```bash
npm run build
npm run build:chat
npm run test:api
npm --prefix apps/chat-frontend run e2e
docker compose config --services
```
