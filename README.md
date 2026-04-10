# Instagram Automation

Instagram automation dashboard with:

- FastAPI backend in server
- React + Vite frontend in frontend

## Project Layout

Important backend runtime files are intentionally inside server:

- Virtual environment: server/.venv
- Python dependencies: server/requirements.txt
- SQLite database: server/instagram.db

## Prerequisites

- Python 3.9 or newer
- Node.js 18 or newer
- npm

## Backend Setup

From project root:

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Start the backend from the server directory (so the database creates there):

```bash
cd server
source .venv/bin/activate
uvicorn app.main:app --reload
```

Backend URLs:

- API base: http://127.0.0.1:8000/api/v1
- Swagger docs: http://127.0.0.1:8000/docs

## Frontend Setup

From project root:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend URL:

- http://localhost:5173

## Run Full Stack

Use two terminals from project root.

Terminal 1 (backend):

```bash
cd server
source .venv/bin/activate
uvicorn app.main:app --reload
```

Terminal 2 (frontend):

```bash
cd frontend
npm run dev
```

## Test Backend

Run tests from the server directory:

```bash
cd server
pytest tests -q
```

## Main API Endpoints

- POST /api/v1/auth/login
- POST /api/v1/auth/logout
- GET /api/v1/auth/status
- GET /api/v1/followers/list
- GET /api/v1/followers/unfollowers
- GET /api/v1/followers/not-following
- GET /api/v1/followers/mutual
- GET /api/v1/followers/stats
- GET /api/v1/analysis/summary
- POST /api/v1/posts/download
- GET /api/v1/health/
- GET /api/v1/health/ready