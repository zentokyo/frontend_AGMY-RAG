# План миграции с Telegram на веб (AGMY RAG)

**Критическое уточнение:** это **полная миграция** с Telegram на веб. После релиза веб-интерфейса **Telegram-бот не используется**. Не требуется дублирование платформ, синхронизация с Telegram, поле `telegram_id` и поддержка двух клиентов параллельно.

Документ опирается на текущий монорепозиторий: `client/` и `server/` (админ-панель), `bot/telegramBot.py`, доменный код и схему БД в `backend/` (до вывода из эксплуатации).

---

## 1. TECH STACK (как у админ-панели)

Админ-панель уже задаёт эталон — веб-приложение для пользователей должно на него опираться.

### Frontend

| Требование | Факт в репозитории (`client/package.json`) |
|------------|---------------------------------------------|
| React | **React 19** |
| Сборка | **Vite 6** |
| Роутинг | **react-router-dom 7** |
| Данные | **@tanstack/react-query 5** |
| HTTP | **axios** |
| Состояние | **zustand** |
| UI / иконки | **lucide-react**, без Material/Ant Design — **кастом на Tailwind** |
| Стили | **Tailwind CSS 3** + слой компонентов в `client/src/index.css` (`.btn`, `.card`, `.input`, …) |
| Уведомления | **react-hot-toast** |
| Утилиты классов | **clsx** |

**Вывод:** новый фронт (`web-app/frontend` или зеркальная структура) копирует **те же версии и паттерны**, что `client/`: Vite-конфиг, Tailwind/PostCSS, структура `components/`, `pages/`, `api/`, `store/`.

### Backend

| Требование | Факт (`server/package.json`) |
|------------|-------------------------------|
| Runtime | **Node.js**, **Express 4** |
| БД | **PostgreSQL** через **pg** |
| Auth | **JWT** (access) + **httpOnly cookie** refresh (см. `server/src/routes/auth.js`) |
| Конфиг | **dotenv**, переменные как в корневом `.env` / `server/.env` (`server/src/env.js`) |

**Вывод:** пользовательское API реализуется в **Node.js + Express**, в той же кодовой базе или в `web-app/backend` с **теми же** зависимостями (bcrypt, jsonwebtoken, cookie-parser, cors).

### Что уходит после миграции

- Сервис **`assistant_backend` (FastAPI)** и HTTP-эндпоинты, которые дергал бот (`/exams`, `/answers`, `/stats`, `/themes`, …) — **подлежат удалению** после переноса логики в Node (или поэтапно: сначала Node-прокси, затем выключение Python).
- Каталог **`bot/`** — **удаление** после релиза веба.
- **Не** проектируем таблицу `telegram_id`, dual-platform auth и синхронизацию.

---

## 2. Анализ функционала бота (`bot/telegramBot.py`) — что перенести в веб

### Авторизация / «регистрация»

| Вопрос | Ответ по коду |
|--------|----------------|
| Как идентифицировались пользователи? | **`user_id = update.effective_user.id`** — целочисленный **Telegram user id**, передавался во все запросы FastAPI. |
| Была ли регистрация? | **Нет.** Отдельной формы регистрации нет; при первом `/start` пользователь уже «известен» API как числовой id. |
| Что сохранялось о пользователе? | В БД через бэкенд — связка **`exam.user_id`**, ответы, экзамены; **отдельной сущности User в моделях Python под бота нет** — только `user_id` в таблице `exam` и производных данных. |

**Для веба:** вводится полноценная модель учётной записи (**email + password_hash**, опционально **username**), JWT-сессия; **`user_id` в доменных таблицах** — внутренний id из новой таблицы `app_users` (или переименованной `users`), **без** привязки к Telegram.

### Основной функционал (экзамены)

В боте **нет команды `/exam`** — экзамен запускается кнопкой **«Начать экзамен»** (и сценарий из «Теория» после выдачи ZIP).

| Элемент | Поведение в боте |
|---------|------------------|
| Старт | `GET /exams/themes/users/{user_id}` — список экзаменационных тем; выбор темы → `POST /exams/` с `user_id`, `question_count` (10 в основном сценарии), `exam_theme_id` при необходимости. |
| Прохождение | `POST /exams/users/{user_id}/questions/ask/` — следующий вопрос; при необходимости `GET .../unanswered/`; ответ текста → `POST /answers/` с `user_id`, `answer_text`. |
| Проверка ответов | На стороне бэкенда (логика use case); бот только показывает результат/следующий шаг. |
| Завершение | По исчерпанию вопросов/логике сессии; затем опционально **«Последний экзамен»** в статистике. |

### Теория

| Элемент | Поведение |
|---------|-----------|
| Вход | Команда **`/theory`** или кнопка **«Теория»** |
| Список тем | `GET /themes/users/{user_id}/` |
| Материалы | `GET /themes/{theme_id}/file/` — **ZIP** (в боте PDF извлекаются из ZIP) |
| Доп. | После выдачи материалов по теме бот создаёт **мини-экзамен на 3 вопроса** (`POST /exams/` с `question_count=3`, `exam_theme_id`) |

### Статистика

| Элемент | Поведение |
|---------|-----------|
| Вход | `/stats` или кнопка **«Статистика»** |
| Общая | `GET /stats/users/{user_id}/all/` — форматирование `format_stats_minimal` (всего ответов, верных, точность, по темам). |
| Последний экзамен | `GET /stats/users/{user_id}/last/` — `format_last_stats_minimal` + список ответов с корректностью. |
| Графики | **Нет** — только текст; на вебе можно добавить графики **сверх** паритета. |

### FSM (состояния)

Состояния `ConversationHandler` (константы):  
`MAIN_MENU`, `EXAM_ASK_COUNT` (в текущем фрагменте не акцент), `EXAM_IN_PROGRESS`, `HELP_MENU`, `STATS_MENU`, `THEORY_MENU`, `EXAM_CHOOSE_THEME`.

| Состояние | Смысл |
|-----------|--------|
| `MAIN_MENU` | Главное меню, кнопки Теория / Помощь / Экзамен / Статистика |
| `EXAM_CHOOSE_THEME` | Выбор темы экзамена |
| `EXAM_IN_PROGRESS` | Идёт экзамен: «Получить вопрос», произвольный текст = ответ |
| `HELP_MENU` | Справка, «Назад» |
| `STATS_MENU` | «Общая статистика» / «Последний экзамен» / «Отмена» |
| `THEORY_MENU` | Выбор темы теории, скачивание, мини-экзамен |

**`context.user_data`:** словари тем экзамена, текущий вопрос (`current_question`), объекты тем и т.д. (воспроизводится в React state + URL при необходимости).

### Прочее

- **`/help`**, **`/start`**, **`/cancel`** — справка, сброс в меню, выход из диалога.
- **Глобальный `on_error`:** сообщение пользователю + возврат клавиатуры главного меню.

---

## 3. Текущая схема БД (релевантная боту)

Отдельной таблицы **`users`** в доменных моделях Python **нет**. Используются (см. `backend/src/core/assistant/models/`):

| Таблица | Назначение |
|---------|------------|
| `exam_theme` | Экзаменационные темы |
| `exam` | Сессии экзаменов; поле **`user_id` (integer)** — сейчас фактически Telegram id |
| `exam_question` | Связь экзамен ↔ вопрос, статус |
| `question` | Текст вопроса, связь с темой обучения |
| `answer` | Ответ пользователя, **is_correct** |
| `theme` | Темы учебных материалов |
| `file` | Имена файлов в хранилище |
| `theme_file` | M:N тема ↔ файл |

Статистика в FastAPI **считается** в use case’ах по `exam` / `answer`, отдельной таблицы «stats» в grep моделей **не обязательно** (уточнять по Alembic при миграции).

Админка (Node) добавляет таблицы **`admin_users`**, **`admin_refresh_tokens`** (`server/src/db/migrations/001_init.sql`) — **это отдельно** от пользователей портала; их **не смешивать** с учётками экзаменов.

### Что изменить при миграции на веб-учётки

1. **Ввести таблицу пользователей портала**, например `app_users`:

   - `id SERIAL PRIMARY KEY` (это и будет новый **`user_id`** для `exam` и связанных сущностей),
   - `email UNIQUE NOT NULL`,
   - `password_hash NOT NULL`,
   - `username` (optional),
   - `created_at`.

2. **Заменить смысл `exam.user_id`:** с Telegram id на **`app_users.id`**. Для существующих строк в БД — одна из стратегий ниже.

3. **Не** добавлять `telegram_id`.

**Пример направления миграции (адаптировать под финальные имена и FK):**

```sql
-- 1) Создать app_users
CREATE TABLE app_users (
  id            SERIAL PRIMARY KEY,
  email         VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  username      VARCHAR(100),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2) Если НУЖНО сохранить старые экзамены:
--    - либо bulk-INSERT в app_users с синтетическим email tg_<old_id>@migrated.local и сопоставление 1:1 old_id -> new id (сложно, если id авто),
--    - либо ОДИН РАЗ: добавить колонку exam.user_id_new, заполнить маппингом, переключить FK, удалить старое.
-- Если старые данные НЕ нужны: TRUNCATE каскадом по зависимостям или новая БД + чистые миграции.
```

**Вопрос продукта (зафиксировать до релиза):** нужно ли сохранять историю экзаменов **Telegram-пользователей**? Если нет — проще **чистая БД** или обнуление доменных таблиц при первом деплое веба.

---

## 4. Архитектура веб-приложения

### Предлагаемая структура каталогов

Соответствие запросу; **альтернатива:** не плодить второй Node-процесс, а расширить существующий `server/src` маршрутами `/api/app/*` и отдельной сборкой фронта `web-app/frontend` — один деплой, одна БД, общий пул соединений.

```
web-app/
├── frontend/                 # React + Vite (как client/)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Auth/         # Login, Register
│   │   │   ├── Layout/       # Header, Sidebar (по образцу client/src/components/Layout)
│   │   │   ├── Exam/         # список тем, сессия, вопрос, результаты
│   │   │   ├── Theory/
│   │   │   └── Stats/
│   │   ├── pages/
│   │   ├── api/              # axios instance + interceptors (как client/src/api/client.js)
│   │   ├── store/            # zustand (auth)
│   │   ├── index.css         # те же @layer components, что в client/
│   │   └── App.jsx
│   ├── package.json          # выровнять с client/package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── Dockerfile            # build + nginx:alpine (см. раздел 7)
│   └── ...
│
├── backend/                  # опционально отдельный сервис; иначе — логика в ../../server/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── auth.js       # register, login, me, refresh, logout (по образцу server, но для app_users)
│   │   │   ├── exams.js
│   │   │   ├── answers.js
│   │   │   ├── stats.js
│   │   │   └── themes.js
│   │   ├── services/         # портированная бизнес-логика из Python use cases
│   │   ├── middleware/auth.js
│   │   └── db/
│   ├── package.json
│   └── Dockerfile
│
└── README.md
```

**Что скопировать из админки:** `package.json` (зависимости), `vite.config.js` (proxy на API), `tailwind.config.js`, `postcss.config.js`, `index.html`, **`index.css`** (стили), паттерны `Layout`/`LoginPage`, `api/client.js`.

---

## 5. API на Node.js (замена FastAPI для пользовательского клиента)

Ниже — **целевая** нормализованная схема REST под JWT. Пути можно префиксовать `/api/app` чтобы не пересекаться с `/api/auth`, `/api/documents`, `/api/questions` админки.

### Auth

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/app/auth/register` | email, password, username? |
| POST | `/api/app/auth/login` | email, password → access + refresh cookie (как в админке) |
| POST | `/api/app/auth/refresh` | обновление access |
| POST | `/api/app/auth/logout` | |
| GET | `/api/app/auth/me` | текущий пользователь |

### Экзамены и ответы (логика из бывших FastAPI handlers)

| Бывший FastAPI (бот) | Назначение |
|----------------------|------------|
| `GET /exams/themes/users/{user_id}` | Темы для экзамена |
| `POST /exams/` | Создать сессию |
| `POST /exams/users/{user_id}/questions/ask/` | Следующий вопрос |
| `GET /exams/users/{user_id}/questions/unanswered/` | Текущий неотвеченный |
| `GET /exams/{exam_id}/questions/` | Список вопросов сессии |
| `POST /answers/` | Отправить ответ |
| `GET /stats/users/{user_id}/all/` | Общая статистика |
| `GET /stats/users/{user_id}/last/` | Последний экзамен |
| `GET /themes/users/{user_id}/` | Темы теории |
| `GET /themes/{theme_id}/file/` | Скачать ZIP |

**Node-эквиваленты (пример именования):** везде **`user_id` из JWT** (сервер не доверяет клиенту).

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/app/exam-themes` | темы экзамена для текущего пользователя |
| POST | `/api/app/exams` | body: `question_count`, `exam_theme_id?` |
| GET | `/api/app/exams/in-progress` | активная сессия |
| GET | `/api/app/exams/:examId` | детали |
| POST | `/api/app/exams/:examId/questions/ask` | следующий вопрос |
| GET | `/api/app/exams/:examId/questions/unanswered` | |
| POST | `/api/app/answers` | `answer_text` (exam/question из контекста бэкенда) |
| GET | `/api/app/stats/all` | |
| GET | `/api/app/stats/last` | |
| GET | `/api/app/theory/themes` | |
| GET | `/api/app/theory/themes/:id/file` | stream ZIP из S3/MinIO (как сейчас для theme files) |

Точные DTO должны **повторить** ответы Python-схем, чтобы фронт перенёс форматирование из бота (`extract_question_text`, `format_*_stats`).

**Что удалить после миграции:** маршруты FastAPI в `backend/src/api/**`, сервис `assistant_backend` в docker-compose, зависимость бота от `EXAM_API_BASE_URL`.

---

## 6. UI/UX (согласованность с админ-панелью)

| Аспект | В админке (`client/`) |
|--------|------------------------|
| UI-kit | **Нет MUI/Ant** — Tailwind + классы `.card`, `.btn-primary`, `.input` |
| Цвета | `slate` фон, акцент **blue-600**, тёмный sidebar **slate-900** |
| Layout | Sidebar + Header + `main` с отступами |
| Шрифт | системный стек через Tailwind default |

**Страницы веб-портала (минимум):** Login, Register, Dashboard, выбор/прохождение экзамена, теория (список + скачивание), статистика, профиль/смена пароля, помощь (статический контент из `/help` бота).

**FSM → веб:** **React Router 7** (как в `client/src/App.jsx`) — маршруты вида `/app/exams`, `/app/exams/:examId`, `/app/theory`, `/app/stats`; локальное состояние (Zustand/React Query) вместо `user_data`.

---

## 7. Контейнеризация

- Текущий **`docker-compose.yml`** уже поднимает `assistant_db`, MinIO, `admin-server` (корневой Dockerfile), опционально `admin-client-dev`.
- **Добавить** сервис **`user-web`** (или объединить фронт портала с общим nginx): build из `web-app/frontend`, порт **например 8080**, прокси к **тому же** Node-процессу, что обслуживает `/api/app`, либо к отдельному `web-app/backend` на **5000** — в зависимости от выбора «один Express» vs «два контейнера Node».

- **Env:** те же `DB_*`, `JWT_*`, `S3_*`, `CLIENT_ORIGIN` / отдельный origin для портала; не дублировать секреты без необходимости.

Шаблоны Dockerfile из промпта (Node 18 vs **20** в репо) — **выровнять на `node:20-alpine`** как в корневом `Dockerfile` админки.

---

## 8. План реализации (фазы)

1. **Подготовка:** зафиксировать стратегию данных (миграция старых `user_id` vs чистая БД); ревью Python use case’ов для переноса в Node.
2. **БД:** миграция `app_users`, смена семантики `exam.user_id`, SQL-тесты на копии.
3. **Backend Node:** маршруты `/api/app/*`, middleware JWT, сервисы экзамен/ответ/стат/темы (порт логики с FastAPI).
4. **Frontend:** новый пакет `web-app/frontend` по шаблону `client/`, экраны и интеграция API.
5. **Compose + README:** сервисы, порты, `.env.example`.
6. **Вывод из эксплуатации:** удаление `bot/`, остановка и удаление Python API из деплоя, чистка `docker-compose` и переменных `EXAM_API_BASE_URL`, `BOT_TOKEN`.
7. **Тесты:** e2e сценарий регистрация → экзамен → статистика; прогон на staging.

---

## 9. Вопросы для уточнения

1. **Данные:** переносим историю экзаменов с Telegram-`user_id` или стартуем **с пустой** доменной областью?
2. **Один или два Node-процесса:** расширяем существующий `server/` или отдельный `web-app/backend`?
3. **Таймер экзамена** и **возврат к предыдущему вопросу** — требуются ли (в боте таймера не было; ответ только вперёд по flow)?
4. **Админка и портал на одном origin** (path-based) или разные поддомены (влияет на cookie/CORS)?

---

## 10. Сопоставление с админ-панелью (ответы на вопросы из промпта)

- **Файл фронта:** `client/package.json` — зависимости перечислены в разделе 1.
- **UI library:** кастом + **Tailwind**, не Material/Ant.
- **Переиспользование:** `index.css`, `Layout`, `LoginPage`, `api/client.js`, `DataTable` при необходимости для списков.

---

*Документ заменяет предыдущую версию плана «дублирования бота»; ориентир — **полная миграция** на веб при **едином стеке** с админ-панелью (React + Vite + Tailwind + Node/Express + PostgreSQL + JWT).*
