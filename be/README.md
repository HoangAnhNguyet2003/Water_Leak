
# RESTful Flask + MongoDB Skeleton

## Quick start
```bash
cd be
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
python run.py
```

## API
Base: /api/v1
- POST   /users
- GET    /users
- GET    /users/{id}
- PATCH  /users/{id}
- DELETE /users/{id}
