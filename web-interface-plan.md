# AGMY RAG — web interface status

Статус на 2026-06-08: веб-интерфейс больше не строится вокруг отдельного
Node/Express backend. Admin и student frontend работают с единым FastAPI.

## Активные части

- `apps/admin-frontend`: React/Vite админка. Production build копируется в
  Python image и отдаётся FastAPI.
- `apps/chat-frontend`: React/Vite пользовательский портал. В dev-режиме Vite
  проксирует `/api` на `http://localhost:8001`.
- `backend`: FastAPI backend для admin API, public app API, auth, documents,
  course/exam lifecycle, RAG и static admin SPA.
- `docker-compose.yml`: PostgreSQL, Qdrant, MinIO, FastAPI backend и bot.

## API ownership

- Admin routes: `/api/auth/*`, `/api/documents/*`, `/api/questions/*`,
  `/api/themes/*`.
- Student routes: `/api/app/auth/*`, `/api/app/themes/*`,
  `/api/app/exam-themes`, `/api/app/exams/*`, `/api/app/answers`,
  `/api/app/stats/*`, `/api/app/course/*`.
- Static admin routes: `/`, `/login`, `/dashboard`, `/knowledge-base`,
  `/questions` are served by FastAPI as SPA fallback.

## Ports

- FastAPI production/local compose: `http://localhost:8001`.
- Admin Vite dev: `http://localhost:5173`.
- Student Vite dev: `http://localhost:5174` or Playwright `4174`.
- PostgreSQL published port: `5433`.
- Qdrant: `6333`.
- MinIO console/API: `7000`, `9001`.

## Next work

1. Keep reducing archive noise: remove or clearly mark unused legacy folders.
2. Improve Python RAG quality with measured changes and regression fixtures.
3. Add e2e coverage for admin document upload and RAG-backed answer scoring.
4. Decide separately whether Telegram bot remains as supported client or moves
   to archival mode.
