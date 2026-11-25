# Deployment Guide — Day 14 Lab

**Họ tên:** LuuThanhMy
**Ngày deploy:** 2026-11-25
**Platform:** Railway

---

## URL Public

```
https://k5-l3a-day14-luuthanhmy-2a202603532-deployment-b-production.up.railway.app
```

## Health Check

```
GET /health
→ {"status": "ok"}
```

## Test API

```bash
# Lấy token
curl -X POST "https://k5-l3a-day14-luuthanhmy-2a202603532-deployment-b-production.up.railway.app/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username": "student", "password": "demo123"}'

# Gọi /ask với token
curl -X POST "https://k5-l3a-day14-luuthanhmy-2a202603532-deployment-b-production.up.railway.app/ask" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
```

---

## Kiến trúc

```
GitHub repo
    ↓ (auto-deploy on push)
Railway
    ├── Service: day14-agent (Dockerfile, root: 06-lab-complete/)
    │     ├── FastAPI app (JWT auth, rate limit, cost guard)
    │     └── Health check: /health
    └── Database: Redis (session storage, rate limit counter)
```

---

## Environment Variables

| Key | Value |
|-----|-------|
| `AGENT_API_KEY` | secret-key-123 |
| `ENVIRONMENT` | production |
| `RATE_LIMIT_PER_MINUTE` | 10 |
| `DAILY_BUDGET_USD` | 10.0 |
| `REDIS_URL` | (injected by Railway) |

---

## So sánh railway.toml vs render.yaml

| | railway.toml | render.yaml |
|--|-------------|-------------|
| Builder | `DOCKERFILE` explicit | Auto-detect Dockerfile |
| Health check | `healthcheckPath = "/health"` | `healthCheckPath: /health` |
| Secret | Thêm qua Railway dashboard | `generateValue: true` / `sync: false` |
| Redis | Add Redis plugin riêng | Thêm service riêng trong yaml |
| Config-as-code | Deprecated từ 2026-12-01 | Vẫn hỗ trợ |
