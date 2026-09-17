# Bankapp with SupabaseDB

There is **no login on this branch** — every endpoint is open. Auth, the admin
role and the React frontend live on the `Frontend` branch. (I forgot to add admin)

## Setup

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r config/requirements.txt 
```

## Database

The connection string is read from a `.env` file at the project root. It is
gitignored and never committed — copy `.env.example` and fill in the real one:

```bash
cp .env.example .env
```

```
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

Get it from **Supabase → Project Settings → Database → Connection string**, and
use the **Session pooler (port 5432)**

```bash
.venv/Scripts/python.exe manage.py migrate
```

## Run

```bash
.venv/Scripts/python.exe manage.py runserver
```

Served from `http://127.0.0.1:8000/api/`.
