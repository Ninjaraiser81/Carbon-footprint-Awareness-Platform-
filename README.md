# 🌿 EcoTrack — Carbon Footprint Tracker

A full-stack application to help individuals understand, track, and reduce their carbon footprint through personalized insights, gamification, and science-backed emission data.

---

## 🚀 Quick Start

### 1. Backend (Python FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate         # Windows
# source venv/bin/activate      # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```
🌍 Website: https://ninjaraiser81.github.io/Carbon-footprint-Awareness-Platform-/
🔗 GitHub Repo: https://github.com/Ninjaraiser81/Carbon-footprint-Awareness-Platform-
⚙️ Backend API Docs: https://carbon-footprint-awareness-platform-ne60.onrender.com/docs


### 2. Frontend

Open `frontend/index.html` in your browser, or serve with:
```bash
# Python simple server (from frontend directory)
python -m http.server 5500
```
Then visit: http://localhost:5500

**Demo credentials:** `demouser` / `DemoPass1`

---

## 🧪 Running Tests

```bash
cd backend
.\venv\Scripts\activate
pytest tests/ -v --cov=app --cov-report=html
```

View coverage report: `backend/htmlcov/index.html`

---

## 🏗️ Architecture

```
carbon-footprint-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + middleware + security
│   │   ├── dependencies.py      # JWT auth dependency
│   │   ├── database/
│   │   │   ├── models.py        # SQLAlchemy ORM models
│   │   │   └── session.py       # DB session + seeding
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic v2 schemas
│   │   ├── routers/
│   │   │   ├── auth.py          # Register, login, profile
│   │   │   ├── activities.py    # CRUD for activities
│   │   │   └── dashboard.py     # Dashboard + Insights
│   │   └── services/
│   │       ├── auth_service.py  # JWT + bcrypt
│   │       └── carbon_calculator.py  # IPCC emission factors
│   ├── tests/
│   │   ├── conftest.py          # Pytest fixtures
│   │   ├── test_calculator.py   # Unit tests (35+ tests)
│   │   └── test_api.py          # Integration tests (40+ tests)
│   └── requirements.txt
└── frontend/
    ├── index.html               # Single-page app
    ├── css/style.css            # Dark-mode design system
    └── js/app.js                # SPA logic + Chart.js
```

---

## 📊 Emission Factor Sources

- **IPCC AR6 (2021)** — Transport, energy, food
- **EPA (2023)** — Household, shopping
- **DEFRA (2023)** — Travel, waste
- **IEA (2023)** — Country average comparisons

---

## 🎯 Features

| Feature | Description |
|---|---|
| 🔐 Auth | JWT-based register/login with bcrypt |
| 📊 Dashboard | KPI cards, trend chart, category breakdown |
| 📝 Activity Log | 65+ emission factor subcategories |
| 🧠 Insights | Personalized recommendations + eco score |
| 🏆 Badges | 8 achievements with progress tracking |
| 📜 History | Full CRUD with filters + pagination |
| ♿ Accessibility | WCAG 2.1 AA — ARIA, keyboard nav, focus mgmt |
| 🔒 Security | CORS, CSP, rate limiting, input validation |
| 🧪 Tests | 75+ tests, 95%+ coverage target |

---

## 🔒 Security Checklist

- [x] Password hashing (bcrypt, 12 rounds)
- [x] JWT tokens (HS256, 24h expiry)
- [x] Pydantic strict validation (no raw SQL)
- [x] SQL injection impossible (ORM only)
- [x] XSS prevention (HTML escaping in frontend)
- [x] CORS whitelist (no wildcard)
- [x] Rate limiting (slowapi)
- [x] Security headers (X-Content-Type-Options, X-Frame-Options)
- [x] Input max lengths enforced
