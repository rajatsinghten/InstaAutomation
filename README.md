# instagram-automation

Instagram automation app with:

- FastAPI backend in `server/`
- React frontend in `frontend/`

Legacy root Python scripts were removed. The root `.venv` was also removed.

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm

## 1. Backend Setup (FastAPI)

From project root:

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Start backend:

```bash
cd /Users/rajat/Developer/Projects/Instaloader
server/.venv/bin/python -m uvicorn server.app.main:app --reload
```

Backend URLs:

- API base: `http://127.0.0.1:8000/api/v1`
- Swagger: `http://127.0.0.1:8000/docs`

## 2. Frontend Setup (React + Vite)

From project root:

```bash
cd frontend
npm install
cp .env.example .env
```

Run frontend:

```bash
npm run dev
```

Frontend URL:

- `http://localhost:5173`

## 3. Run Both Together

Use two terminals.

Terminal 1 (backend):

```bash
cd /Users/rajat/Developer/Projects/Instaloader
server/.venv/bin/python -m uvicorn server.app.main:app --reload
```

Terminal 2 (frontend):

```bash
cd /Users/rajat/Developer/Projects/Instaloader/frontend
npm run dev
```

## 4. Backend Test Command

Always run tests with backend venv:

```bash
cd /Users/rajat/Developer/Projects/Instaloader
server/.venv/bin/python -m pytest server/tests -q
```

## Main API Endpoints

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/status`
- `POST /api/v1/engagement/calculate`
- `POST /api/v1/followers/export`
- `POST /api/v1/posts/download`
- `POST /api/v1/profile/picture`