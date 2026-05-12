# Deep Skin Project Instructions

Welcome to the Deep Skin project. This document provides foundational guidance on the project's architecture, technologies, and development workflows.

## Project Overview

Deep Skin is an AI-powered skin analysis platform. It allows users to upload or capture facial images, which are then analyzed by AI models to provide detailed skin health reports and personalized skincare product recommendations.

### Core Architecture

- **Backend (`/backend`):** A FastAPI-based REST API that handles user authentication (JWT), profile management, image uploads, analysis sessions, and recommendation logic. It uses SQLAlchemy with a MySQL database.
- **Frontend (`/frontend`):** A Streamlit-based web application providing a user-friendly interface for the analysis flow. It features custom routing and styling to provide a modern service-like experience.
- **AI/ML (`/notebooks`, `/configs`):** Research and training scripts for the skin analysis models (e.g., Pore, Cheek analysis) using PyTorch.

## Technologies & Tools

- **Languages:** Python 3.12+
- **Backend:** FastAPI, SQLAlchemy, Alembic (Migrations), MySQL, Pydantic, JWT.
- **Frontend:** Streamlit, Requests, CSS.
- **Package Manager:** `uv` (standardizing on `pyproject.toml` and `uv.lock`).
- **Development:** Jupyter (for research), Pytest.

## Getting Started

### Backend Setup
1. Navigate to the backend directory: `cd backend`
2. Install dependencies: `pip install -r requirements.txt` (or use `uv pip install`)
3. Configure environment variables in `.env` (refer to `app/core/config.py`).
4. Run migrations: `alembic upgrade head`
5. Start the server: `python -m uvicorn app.main:app --reload`

### Frontend Setup
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `pip install -r requirements.txt`
3. Start the application: `streamlit run app.py`

## Development Conventions

### Backend
- **Surgical Updates:** When modifying API logic, ensure you update the corresponding service (`app/services/`) and model (`app/models/`) if necessary.
- **Database Migrations:** Always use Alembic for schema changes.
- **Documentation:** Refer to `backend/docs/` for detailed API and DB design specs.
- **Testing:** Use `scripts/run_test.py` for integration tests.

### Frontend
- **Routing:** Managed manually in `app.py`. Do not use Streamlit's native `pages/` directory.
- **Components:** Reuse UI elements from `frontend/components/`.
- **API Calls:** All external communication must go through `frontend/services/api_client.py` or specific API services.
- **Styling:** Use `frontend/styles/` for CSS injections.

### General
- **Instructions:** Always check `backend/AGENTS.md` and `frontend/AGENTS.md` for role-specific instructions.
- **Documentation First:** Update relevant documentation in `docs/` folders whenever architectural or API changes are made.

## Key Files

- `backend/app/main.py`: Backend entry point and router registration.
- `frontend/app.py`: Frontend entry point and routing logic.
- `backend/docs/agent_backend_overview.md`: Comprehensive backend flow description.
- `frontend/docs/frontend_overview.md`: Frontend user flow and design criteria.
- `backend/alembic/versions/`: Database migration history.
- `pyproject.toml`: Root project configuration and dependencies.
