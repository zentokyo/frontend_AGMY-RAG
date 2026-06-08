# Веб-портал AGMY RAG (миграция с Telegram)

> Архивная директория. Актуальный пользовательский frontend находится в
> `apps/chat-frontend`, а API обслуживается FastAPI на `http://localhost:8001`.

## Фаза 1 (текущая) — готово

- Каталог `frontend/`: React 19 + Vite 6 + Tailwind 3, те же зависимости, что у `../client/`.
- Стили: скопирован `index.css` с `@layer components` (`.btn`, `.card`, …).
- Dev-сервер: порт **5174**, прокси `/api` → `http://localhost:8001`.
- Компоненты `Layout`: `AppLayout`, `Sidebar` (навигация портала), `Header` (заглушка пользователя + выход).
- Маршруты: `/login`, `/register`, `/app` и вложенные страницы-заглушки.
- `store/authStore.js` и `api/client.js` — минимальные заготовки под фазы 3–4.

## Запуск в разработке

Из корня репозитория:

```bash
cd web-app/frontend && npm install && npm run dev
```

Откройте **http://localhost:5174**. Production admin SPA отдаётся FastAPI на
**http://localhost:8001**, dev-сервер админки при необходимости остаётся на
**http://localhost:5173**.

## Сборка

```bash
cd web-app/frontend && npm run build
```

Артефакты в `web-app/frontend/dist/`.

## Следующие фазы

См. `web-interface-plan.md`: активный API `/api/app/*` обслуживается FastAPI.
