# Instagram Chatbot — Startup Guide

> Run each service in a **separate terminal**. Order matters for the first start.

---

## Prerequisites

- **WSL** (Ubuntu) with Docker Desktop integration
- **Node.js** ≥ 18 and **npm**
- **Python** 3.12+ with **venv**
- **PostgreSQL** 14+

---

## 1. Docker Daemon (WSL)

If using WSL, Docker Desktop must be running on Windows with WSL integration enabled.
If `docker ps` gives a permission error:

```bash
# One-time fix: add yourself to the docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker ps
```

---

## 2. PostgreSQL

### Option A: Already installed as system service

```bash
# Check status
sudo service postgresql status

# Start if not running
sudo service postgresql start
```

### Option B: Run via Docker

```bash
docker run -d \
  --name postgres \
  -e POSTGRES_USER=chatbot_user \
  -e POSTGRES_PASSWORD=chatbot_secure_2026 \
  -e POSTGRES_DB=instagram_chatbot \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16
```

### Verify connection

```bash
psql postgresql://chatbot_user:chatbot_secure_2026@localhost:5432/instagram_chatbot -c "SELECT 1;"
```

---

## 3. Qdrant (Vector Database)

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  qdrant/qdrant
```

### Verify

```bash
curl http://localhost:6333
# Should return: {"title":"qdrant","version":"..."}
```

### Dashboard

Open [http://localhost:6333/dashboard](http://localhost:6333/dashboard) in your browser.

---

## 4. Backend (FastAPI)

```bash
cd backend

# First time only: create venv & install deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start dev server (with auto-reload + ngrok tunnel)
source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will:
- Create database tables automatically
- Start an ngrok tunnel (if `NGROK_AUTH_TOKEN` is set in `.env`)
- Print the public webhook URL

### Verify

```bash
curl http://localhost:8000
# Should return: {"status":"ok","service":"instagram-chatbot"}
```

---

## 5. Frontend (Vite + React)

```bash
cd frontend

# First time only: install deps
npm install

# Start dev server
npm run dev
```

### Access

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Quick Start (all at once)

Open **4 terminals** and run in order:

| Terminal | Command |
|----------|---------|
| 1 | `sudo service postgresql start` |
| 2 | `docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage qdrant/qdrant` |
| 3 | `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| 4 | `cd frontend && npm run dev` |

---

## Stopping Services

```bash
# Backend / Frontend: Ctrl+C in their terminals

# Qdrant
docker stop qdrant

# PostgreSQL (if system service)
sudo service postgresql stop

# Restart stopped containers later
docker start qdrant
```

---

## Ports Summary

| Service    | Port  | URL                          |
|------------|-------|------------------------------|
| Backend    | 8000  | http://localhost:8000        |
| Frontend   | 5173  | http://localhost:5173        |
| PostgreSQL | 5432  | —                            |
| Qdrant     | 6333  | http://localhost:6333        |
| Qdrant gRPC| 6334  | —                            |
| ngrok      | 4040  | http://localhost:4040        |
