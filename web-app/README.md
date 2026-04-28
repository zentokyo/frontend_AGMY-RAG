# Веб-портал AGMY RAG (миграция с Telegram)

## Фаза 1 (текущая) — готово

- Каталог `frontend/`: React 19 + Vite 6 + Tailwind 3, те же зависимости, что у `../client/`.
- Стили: скопирован `index.css` с `@layer components` (`.btn`, `.card`, …).
- Dev-сервер: порт **5174**, прокси `/api` → `http://localhost:3001`.
- Компоненты `Layout`: `AppLayout`, `Sidebar` (навигация портала), `Header` (заглушка пользователя + выход).
- Маршруты: `/login`, `/register`, `/app` и вложенные страницы-заглушки.
- `store/authStore.js` и `api/client.js` — минимальные заготовки под фазы 3–4.

## Запуск в разработке

Из корня репозитория:

```bash
cd web-app/frontend && npm install && npm run dev
```

Откройте **http://localhost:5174** (админ-панель по-прежнему на 5173).

## Сборка

```bash
cd web-app/frontend && npm run build
```

Артефакты в `web-app/frontend/dist/`.

## Следующие фазы

См. `web-interface-plan.md`: миграция БД (`app_users`), API `/api/app/*` в `server/`, полноценные формы и интеграция.
