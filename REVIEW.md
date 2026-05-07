# Code Review: AGMY RAG Project

## Общая оценка

**Вердикт:** Проект требует существенной доработки перед production-релизом.

**Общий балл:** 5/10

---

## 1. Архитектура и структура проекта

### 1.1 Монорепозиторий

Проект представляет собой монорепозиторий с несколькими независимыми приложениями:

| Приложение | Назначение | Стек |
|------------|-----------|------|
| `backend/` | FastAPI-бэкенд (AI-ассистент с GigaChat) | Python 3.12, FastAPI, asyncpg, Dishka |
| `bot/` | Telegram-бот | python-telegram-bot |
| `apps/api/` | Node.js API (админка + пользовательский портал) | Express, PostgreSQL |
| `apps/admin-frontend/` | Админ-панель | React 19, Vite, Tailwind |
| `apps/chat-frontend/` | Пользовательский портал | React 19, Vite, Tailwind |

**Проблемы:**

- Дублирование функциональности: FastAPI (`backend/`) и Node.js API (`apps/api/`) обещают один и тот же функционал экзаменов/ответов/статистики
- Согласно `web-interface-plan.md`, после миграции на веб планировалось удалить `backend/` и `bot/`, но этого не сделано
- Две разные БД (PostgreSQL) с общей схемой создают путаницу
- Нет четкого разделения ответственности между сервисами

### 1.2 Структура папок

```
frontend_AGMY-RAG/
├── apps/
│   ├── api/              # Node.js API (Express)
│   ├── admin-frontend/  # React admin
│   └── chat-frontend/    # React portal
├── backend/             # FastAPI backend
├── bot/                 # Telegram bot
├── python/              # Admin tools
├── converters/          # Document converters
├── theme_files/          # PDFs
└── docker-compose.yml
```

**Оценка:** Структура логичная, но:

- `python/` и `converters/` не интегрированы в основной workflow
- Нет общего `shared/` или `packages/` для переиспользуемого кода
- Дублирование конфигурационных файлов (package.json в каждом приложении)

---

## 2. Технологический стек

### 2.1Frontend (React)

| Зависимость | Версия | Оценка |
|-------------|--------|--------|
| React | 19.0.0 | Новинка, возможны проблемы с совместимостью |
| Vite | 6.1.0 | Актуально |
| react-router-dom | 7.4.1 | Актуально |
| @tanstack/react-query | 5.74.4 | Актуально |
| Zustand | 5.0.3 | Актуально |
| Tailwind CSS | 3.4.17 | Актуально |
| lucide-react | 0.475.0 | Актуально |

**Проблемы:**

- React 19 вышел недавно (октябрь 2024), ограниченная экосистема сторонних библиотек
- Использование `react-hot-toast` вместе с TanStack Query может приводить к конфликтам

### 2.2 Backend (Node.js)

| Зависимость | Версия |
|-------------|--------|
| Express | 4.21.2 |
| jsonwebtoken | 9.0.2 |
| bcryptjs | 2.4.3 |
| pg | 8.13.3 |
| @aws-sdk/client-s3 | 3.1035.0 |
| multer | 1.4.5-lts.1 |

**Проблемы:**

- Нет TypeScript — динамическая типи��ация увеличивает риск ошибок
- Нет централизованной валидации запросов (используется `express-validator`, но непоследовательно)
- Минимальная обработка ошибок

### 2.3 Backend (Python)

| Зависимость | Версия |
|-------------|--------|
| FastAPI | Последняя |
| asyncpg | Последняя |
| Dishka | Последняя (dependency injection) |
| GigaChat SDK | - |

**Проблемы:**

- Python и Node.js делают одно и то же (экзамены, ответы, статистика)
- Нет единого источника истины — бизнес-логика дублируется

---

## 3. Безопасность

### 3.1 Аутентификация и авторизация

**Node.js API (`apps/api/`):**

- JWT с access + refresh токенами
- Refresh-токен хранится в httpOnly cookie
- Bcrypt с cost 12 для паролей
- Используется `crypto` для хеширования токенов

**Проблемы:**

```javascript
// apps/api/src/routes/app/auth.js:64
res.cookie(COOKIE_NAME, refreshToken, {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',  // Только в production!
  sameSite: 'strict',
  maxAge: REFRESH_EXPIRES_MS,
})
```

**Рекомендация:** Добавить флаг `secure: true` для production-режима и гарантировать работу только через HTTPS.

- Нет rate limiting
- Нет защиты от brute force
- Нет MFA
- Отсутствует password reset flow

### 3.2 CORS

```javascript
// apps/api/src/app.js:32
app.use(cors({
  origin: corsOrigin,
  credentials: true,
}))
```

**Проблемы:**

- CORS настроен через переменную `CLIENT_ORIGIN` — если не настроена, используется `localhost`
- `credentials: true` при динамическом origin потенциально опасно

### 3.3 База данных

- Пароли подключения к БД в переменных окружения
- Нет шифрования данных
- Нет audit logs
- Нет RLS (Row Level Security)

### 3.4 Загрузка файлов

```javascript
// apps/api/src/middleware/upload.js
// multer без ограничений размера
```

**Проблемы:**

- Нет ограничения размера файла
- Нет валидации типов файлов
- Загруженные файлы хранятся локально (не в S3/MinIO)

---

## 4. Качество кода

### 4.1 Node.js API

**Проблемы структуры:**

- Все роутеры в одной директории `apps/api/src/routes/`
- Нет сервис-слоя — бизнес-логика в роутерах
- Нет единой точки входа для ошибок
- Дублирование SQL-запросов

**Пример:**

```javascript
// apps/api/src/routes/app/auth.js:27-75
router.post('/register', async (req, res, next) => {
  try {
    const { email, password, username } = req.body
    // Вся логика в роутере — нет разделения concerns
  } catch (err) {
    next(err)
  }
})
```

**Рекомендация:** Ввести сервисный слой:

```
apps/api/src/
├── routes/
│   └── auth.js        # Только HTTP
├── services/
│   └── authService.js # Бизнес-логика
├── models/
│   └── userModel.js   # Работа с БД
└── middleware/
    └── auth.js
```

### 4.2 React Frontend

**Положительные моменты:**

- Использование TanStack Query для серверного состояния
- Zustand для клиентского состояния
- Разделение на компоненты и страницы
- Использование Tailwind CSS

**Проблемы:**

- Нет TypeScript
- Нет unit tests
- Ограниченная документация компонентов
- Нет единого подхода к обработке ошибок

### 4.3 Python Backend

```python
# backend/src/main.py
app.include_router(theme_router)
app.include_router(exam_theme_router)
# ... 6 роутеров
```

**Проблемы:**

- FastAPI и Node.js API дублируют функционал
- Нет общей схемы между Python и Node API
- Dishka (DI) усложняет понимание flow

---

## 5. Базы данных и миграции

### 5.1 PostgreSQL

**Схема БД:**

- Общая БД `assistant` для всех сервисов
- Таблицы админки: `admin_users`, `admin_refresh_tokens`
- Таблицы портала: `app_users`, `app_refresh_tokens`
- Доменные таблицы: `exam`, `exam_theme`, `question`, `answer`, `theme`, `file`

**Проблемы:**

- Нет foreign keys между `app_users` и `exam` (используется old `user_id`)
- Смешение сущностей в одной БД
- Нет миграций для Python (Alembic настроен, но непонятно, применяются ли)
- Нет версионирования схемы

### 5.2 Миграции Node.js

```javascript
// apps/api/src/db/migrate.js
// Простой SQL-скрипт без версионирования
```

**Проблемы:**

- Нет Alembic-like инструмента
- Нет down-миграций
- Нет seed-данных для портала

---

## 6. DevOps и развертывание

### 6.1 Docker Compose

```yaml
# docker-compose.yml
services:
  assistant_db: postgres:17-alpine
  assistant-file-storage: minio/minio
  assistant_backend: FastAPI
  assistant_bot: Telegram
  admin-server: Node.js + React
```

**Проблемы:**

- 6 сервисов — избыточная сложность, если планируется миграция на веб
- Нет healthchecks для всех сервисов
- Нет мониторинга
- Нет логирования

### 6.2 Сборка

```bash
# package.json
"build": "npm --prefix apps/admin-frontend run build"
```

**Проблемы:**

- нет CI/CD
- нет автоматических тестов
- нет линтеров в pre-commit hook

---

## 7. Тестирование

### 7.1 Текущее состояние

- E2E тесты на Playwright (`apps/chat-frontend/e2e/`)
- API тесты (`tests/api/`)
- Нет unit тестов
- Нет интеграционных тестов

**Проблемы:**

- Тесты не запускаются автоматически
- Охват неизвестен
- Нет тестов для Python backend

---

## 8. Конкретные уязвимости и проблемы

### 8.1 Критические

1. **Дублирование API:** FastAPI и Node.js обеспечивают один функционал — нужно выбрать один
2. **Отсутствие SSL в development:** `secure: process.env.NODE_ENV === 'production'`
3. **Нет rate limiting:** Уязвимость к DoS-атакам

### 8.2 Высокие

1. **Загрузка файлов без валидации:** Размер, типы файлов не проверяются
2. **CORS wildcard:** Потенциально открыт для любого origin
3. **Отсутствие логирования:** Нет централизованного лога
4. **Дублирование user_id:** `exam.user_id` все еще использует старую схему

### 8.3 Средние

1. **Нет TypeScript:** Увеличен риск runtime-ошибок
2. **Нет документации API:** Только код
3. **Нет раздельных окружений:** dev и prod смешаны
4. **Нет мониторинга:** Нет Prometheus/Grafana

### 8.4 Низкие

1. **Дублирование зависимостей:** Одинаковые пакеты в разных apps
2. **Нет общих компонентов:** Два React-приложения не шарится кодом
3. **Нет accessibility:** Не проверялась доступность

---

## 9. Рекомендации по исправлению

### 9.1 Приоритет 1 — Безопасность

- [ ] Добавить rate limiting (`express-rate-limit`)
- [ ] Ограничить размер загружаемых файлов
- [ ] Валидировать типы файлов при загрузке
- [ ] Настроить HTTPS everywhere
- [ ] Ввести CSRF protection

### 9.2 Приоритет 2 — Архитектура

- [ ] Определиться с одним backend: FastAPI или Node.js
- [ ] Удалить неиспольз��емые сервисы (`bot/`, один из API)
- [ ] Ввести сервисный слой в Node.js API
- [ ] Добавить TypeScript

### 9.3 Приоритет 3 — Качество

- [ ] Ввести ESLint + Prettier
- [ ] Написать unit тесты (Jest/Vitest)
- [ ] Настроить CI/CD (GitHub Actions)
- [ ] Добавить документацию

### 9.4 Приоритет 4 — DevOps

- [ ] Настроить мониторинг
- [ ] Настроить centralized logging
- [ ] Добавить healthchecks
- [ ] Настроить backup PostgreSQL

---

## 10. Заключение

Проект представляет собой **миграцию с Telegram на веб** и содержит устаревший код (FastAPI backend и Telegram bot), который должен быть удален после полного перехода на веб-портал.

**Основные проблемы:**

1. Дублирование функционала между Python и Node.js
2. Отсутствие базовых мер безопасности
3. Нет TypeScript → высокий риск ошибок
4. Нет автоматического тестирования
5. Смешение dev и prod конфигураций

**Следующие шаги:**

1. Определиться с архитектурой (один backend)
2. Удалить неиспользуемые сервисы
3. Ввести TypeScript
4. Настроить безопасность
5. Ввести CI/CD

Проект требует **существенной доработки** перед production-релизом. Рекомендуемое время на исправление: **2-3 месяца**.