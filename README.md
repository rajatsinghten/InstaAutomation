# Instagram Automation Dashboard 📸

An interactive Instagram automation and analytics dashboard designed to help you track followers, unfollowers, mutuals, and other Instagram metrics seamlessly. 

The project is built with a modern backend and frontend architecture, ensuring optimal performance, scalability, and ease of use.

---

## 🛠️ Tech Stack & Key Libraries

### Backend (Python / FastAPI) 🐍
The backend resides in the `server/` directory and is responsible for all heavy lifting, scraping, data analysis, and API provisioning.

**Core Framework & Server**
- **[FastAPI](https://fastapi.tiangolo.com/)**: A modern, highly performant web framework for building APIs. Used for its auto-docs, speed, and standard Python type hints.
- **[Uvicorn](https://www.uvicorn.org/)**: An ASGI web server implementation used to run the FastAPI application.
- **[Pydantic](https://docs.pydantic.dev/)**: Data validation and settings management using Python type annotations.

**Instagram APIs & Web Scraping**
- **[Instagrapi](https://subdapandey.github.io/instagrapi/)**: A powerful unofficial Instagram API wrapper to fetch followers, posts, and handle interactions.
- **[Playwright](https://playwright.dev/python/)**: Headless browser automation framework, typically used to solve complex login flows or bypass web scraping bottlenecks.

**Database & Caching**
- **[SQLAlchemy](https://www.sqlalchemy.org/)** & **Aiosqlite**: An asynchronous SQL database toolkit and Object-Relational Mapping (ORM) library connecting to local SQLite databases (`server/instagram.db`).
- **[Alembic](https://alembic.sqlalchemy.org/)**: A lightweight database migration tool for SQLAlchemy.
- **[Redis](https://redis.io/)**: An in-memory data structure store used for caching API outputs, session storage, and rate-limiting.

**Security & Utilities**
- **PyJWT & Passlib**: Used for securely hashing passwords and generating stateless JSON Web Tokens for authentication.
- **Slowapi**: A rate-limiting library for FastAPI to protect endpoints from spam/abuse.
- **Pandas & NumPy**: Extremely fast data manipulation libraries used to calculate "Not Following Back", "Mutuals", and other analytics efficiently.
- **Tenacity**: A general-purpose retrying library to handle flaky network requests.
- **Pytest**: Used for comprehensive API and logic testing.

### Frontend (React / Vite) ⚛️
The user interface is maintained within the `frontend/` directory.

- **[React 19](https://react.dev/)**: The dominant JavaScript library for building component-based user interfaces.
- **[Vite](https://vitejs.dev/)**: A next-generation frontend bundler providing instantaneous Hot Module Replacement (HMR) and faster builds compared to traditional bundlers like Create React App.
- **ESLint**: Linter for identifying and fixing JS/JSX problems.

---

## 📂 Project Layout

```text
├── frontend/             # React + Vite UI application
│   ├── src/              # React components and assets
│   ├── package.json      # Frontend dependencies
│   └── vite.config.js    # Bundler configuration
├── server/               # FastAPI backend application
│   ├── app/              # Main application logic (API, models, services)
│   ├── tests/            # Pytest test suites
│   ├── alembic.ini       # Migration configs
│   └── requirements.txt  # Python backend dependencies
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.9+**
- **Node.js 18+** & **npm**
- **Redis** Server (make sure Redis is running locally or configured)

---

### Backend Setup

1. Navigate to the server folder and set up a virtual environment:
   ```bash
   cd server
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Setup environment variables:
   ```bash
   cp .env.example .env
   ```

4. Start the backend:
   ```bash
   # Run from the 'server' directory to correctly initialize the SQLite database
   uvicorn app.main:app --reload
   ```
   **Backend URLs:**
   - **API base:** http://127.0.0.1:8000/api/v1
   - **Swagger Docs:** http://127.0.0.1:8000/docs

---

### Frontend Setup

1. Open a new terminal instance and navigate to the frontend:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Setup your environment configurations:
   ```bash
   cp .env.example .env
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```
   **Frontend URL:** http://localhost:5173

---

## 🧪 Testing the API

To run the backend test suite, use pytest from within the `server` directory:

```bash
cd server
source .venv/bin/activate
pytest tests -v
```

---

## 📡 Main API Endpoints

Once your server is running, you can hit the following core endpoints, or explore them natively at **http://127.0.0.1:8000/docs**:

**Auth**
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/status`

**Followers Analytics**
- `GET /api/v1/followers/list`
- `GET /api/v1/followers/unfollowers`
- `GET /api/v1/followers/not-following`
- `GET /api/v1/followers/mutual`
- `GET /api/v1/followers/stats`

**General Analytics**
- `GET /api/v1/analysis/summary`

- POST /api/v1/posts/download
- GET /api/v1/health/
- GET /api/v1/health/ready