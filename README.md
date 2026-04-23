# AGMY-RAG Admin Panel

Web-based administration interface for managing the AGMY RAG assistant's Knowledge Base (documents) and Question Database (Q&A pairs).

## Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Frontend   | React 19, Vite, Tailwind CSS        |
| Backend    | Node.js, Express                    |
| Database   | PostgreSQL                          |
| Auth       | JWT (access + refresh token rotation) |
| RAG Bridge | ChromaDB via Python subprocess      |

## Prerequisites

- Node.js >= 18
- PostgreSQL >= 14 (or Docker)
- Python 3.10+ with the `ai_support` project cloned alongside this repo
- The `ai_support` virtual environment activated (for `ingest.py` / `admin_tools.py`)

## Directory Layout

```
frontend_AGMY-RAG/
├── client/          React + Vite + Tailwind SPA
├── server/          Node.js + Express API
├── python/          admin_tools.py (ChromaDB deletion helper)
└── docker-compose.yml
```

## Quick Start

### 1. Install dependencies

```bash
npm run install:all
```

### 2. Configure environment

```bash
cp server/.env.example server/.env
# Edit server/.env — set DB credentials, JWT secrets, and paths to ai_support
```

### 3. Start PostgreSQL

```bash
# Via Docker (recommended)
docker compose up -d postgres

# Or use your local PostgreSQL instance
```

### 4. Run migrations and seed

```bash
npm run db:migrate
npm run db:seed      # creates the first admin user from .env SEED_ADMIN_* vars
```

### 5. Start development servers

```bash
npm run dev
# → API server: http://localhost:3001
# → React dev:  http://localhost:5173
```

### Production build

```bash
npm run build        # builds client into server/public/
npm run start        # serves API + static files on port 3001
```

## Environment Variables

See [`server/.env.example`](server/.env.example) for the full list.

Key variables:

| Variable              | Description                                     |
|-----------------------|-------------------------------------------------|
| `DB_*`                | PostgreSQL connection                           |
| `JWT_SECRET`          | Secret for access tokens                        |
| `JWT_REFRESH_SECRET`  | Secret for refresh tokens                       |
| `KB_PATH`             | Path to `ai_support/knowledge_base/`            |
| `INGEST_SCRIPT_PATH`  | Path to `ai_support/ingest.py`                  |
| `ADMIN_TOOLS_PATH`    | Path to `python/admin_tools.py`                 |
| `SEED_ADMIN_EMAIL`    | Email for the seeded admin account              |
| `SEED_ADMIN_PASSWORD` | Password for the seeded admin account           |

## API Routes

| Method | Path                      | Description                         |
|--------|---------------------------|-------------------------------------|
| POST   | /api/auth/login           | Login → JWT tokens                  |
| POST   | /api/auth/refresh         | Refresh access token                |
| POST   | /api/auth/logout          | Revoke refresh token                |
| GET    | /api/documents            | List knowledge base documents       |
| POST   | /api/documents/upload     | Upload document (triggers ingest)   |
| DELETE | /api/documents/:id        | Delete document (removes from ChromaDB) |
| GET    | /api/documents/stats      | Aggregated document stats           |
| GET    | /api/questions            | Paginated Q&A list                  |
| POST   | /api/questions            | Create Q&A pair                     |
| PUT    | /api/questions/:id        | Update Q&A pair                     |
| DELETE | /api/questions/:id        | Delete Q&A pair                     |
| GET    | /api/questions/stats      | Q&A statistics                      |
