# JevFlow Docker & Containerization Guide

## 1. Overview

JevFlow is containerized with multi-service **Docker Compose** orchestration:
1. **`redis`**: High-performance in-memory cache and token bucket rate limiter (using local `redis:7`).
2. **`backend`**: FastAPI Adaptive AI Gateway powered by System One decisions and real model providers (OpenRouter/OpenAI).
3. **`frontend`**: Next.js (TypeScript, React 19) Observability & Evaluation Dashboard.

---

## 2. Architecture Diagram

```
                 Browser / Client (Port 3000)
                              │
                              ▼
                ┌───────────────────────────┐
                │     jevflow-frontend      │
                │     (Next.js App)         │
                └─────────────┬─────────────┘
                              │
                              ▼ (Port 8000)
                ┌───────────────────────────┐
                │      jevflow-backend      │
                │      (FastAPI Core)       │
                └──────┬──────────────┬─────┘
                       │              │
        (Port 6379)    ▼              ▼ (External HTTPS)
        ┌───────────────────┐   ┌────────────────────────┐
        │   jevflow-redis   │   │  OpenRouter / TypeSafe │
        │   (Redis:7 Cache) │   │  Live Inference APIs   │
        └───────────────────┘   └────────────────────────┘
```

---

## 3. Quickstart: Running with Docker Compose

### 1. Ensure `.env` is configured
Make sure your OpenRouter API key is set in `.env`:
```ini
OPENAI_API_KEY=sk-or-v1-your_openrouter_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
SMALL_MODEL_NAME=meta-llama/llama-3.1-8b-instruct:free
FRONTIER_MODEL_NAME=anthropic/claude-3.5-sonnet

# Optional TypeSafe API Key
TYPESAFE_API_KEY=
```

### 2. Start the Entire Stack
```bash
docker compose up -d
```

### 3. Check Service Status & Logs
```bash
# View running containers
docker compose ps

# Follow logs
docker compose logs -f

# Follow backend logs specifically
docker compose logs -f backend
```

### 4. Access Endpoints
- **Next.js Observability Dashboard:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Core & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Gateway Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

### 5. Stop the Stack
```bash
docker compose down
```
To remove persistent database and cache volumes:
```bash
docker compose down -v
```
