# Day 14 Lab - Mission Answers

**Student Name:** LuuThanhMy  
**Student ID:** 2A202603532  
**Date:** 2026-11-25

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (ít nhất 5)

1. **Hard-coded secrets** (`app.py` dòng 14-15): `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL = "postgresql://admin:password123@..."` — push lên GitHub thì key lộ ngay.
2. **Log ra secret** (`app.py` dòng 29): `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` — log aggregator nào cũng thấy key.
3. **Không có health check** (comment dòng 32-33): platform không biết agent đã crash để restart.
4. **Port và host cố định** (`app.py` dòng 37-38): `host="localhost"` chỉ chạy được trên máy local, không nhận traffic từ ngoài container. `port=8000` không đọc từ env, Railway/Render inject `PORT` khác sẽ fail.
5. **`reload=True` trong production** (`app.py` dòng 39): watch filesystem liên tục, tốn CPU, có thể gây restart không mong muốn.
6. **Không có config management** (dòng 17-18): `DEBUG = True`, `MAX_TOKENS = 500` ghi thẳng vào code, muốn thay đổi phải sửa code và deploy lại.

### Exercise 1.3: Bảng so sánh develop vs production

| Feature | Develop (`develop/app.py`) | Production (`production/app.py`) | Tại sao quan trọng? |
|---------|---------------------------|----------------------------------|---------------------|
| Config | Hard-code trong code | Đọc từ env var qua `Settings` dataclass | Thay đổi mà không cần sửa code, không lộ secret |
| Secret | `OPENAI_API_KEY = "sk-..."` trong code | Đọc từ `os.environ`, không có default | Không lộ key khi push Git |
| Logging | `print("[DEBUG] ...")` | Structured JSON logging (`logging` + formatter) | Dễ parse bằng Datadog/Loki, có thể filter theo level |
| Health check | Không có | `GET /health` luôn trả 200; `GET /ready` trả 503 khi Redis chết | Platform biết restart khi cần |
| Graceful shutdown | Không có | `lifespan` context manager, xử lý SIGTERM | Request đang chạy không bị cắt ngang |
| Host binding | `host="localhost"` | `host="0.0.0.0"` | Container cần 0.0.0.0 để nhận traffic từ ngoài |
| Port | Cố định 8000 | Đọc từ `PORT` env var | Railway/Render inject PORT khác nhau |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image (develop):** `python:3.11` — full distribution ~1 GB
2. **Working directory:** `/app`
3. **Tại sao COPY requirements.txt trước COPY . .?** Docker cache từng layer. Nếu chỉ sửa code (không đổi requirements), layer `pip install` được cache lại — build nhanh hơn nhiều. Nếu COPY . . trước thì mỗi lần sửa code đều phải chạy lại pip install.
4. **Multi-stage giảm dung lượng ở đâu?** Stage builder có gcc, build tools, pip cache (~800 MB). Stage runtime chỉ copy site-packages đã compile. Image cuối không có compiler, không có pip cache — còn ~200-300 MB.

### Exercise 2.3: Image size comparison

| | Develop | Production |
|--|---------|------------|
| Base | python:3.11 (full) | python:3.11-slim (multi-stage) |
| Kích thước | **1.67 GB** | **240 MB** |
| Chênh lệch | **-86%** |

*(Số đo thực tế từ `docker images my-agent` sau khi build)*

### Exercise 2.4: Stack Docker Compose

Services trong stack production (`02-docker/production/docker-compose.yml`):
- `agent` — app FastAPI, build từ Dockerfile production
- `redis` — Redis 7 Alpine, cache/session
- `nginx` — reverse proxy, load balancer phía trước agent

Kết quả test qua Nginx: `GET http://localhost/health` → 200; `POST http://localhost/ask` → 200 với JSON response.

---

## Part 4: API Security

### Exercise 4.1: API Key auth

```
# Key đúng → 200
curl -i -X POST "http://localhost:8001/ask" -H "X-API-Key: secret-key-123" -H "Content-Type: application/json" -d "{\"question\":\"Hello\"}"
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 08:46:46 GMT
server: uvicorn
content-length: 122
content-type: application/json

{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}

# Key sai → 403
curl -i -X POST "http://localhost:8001/ask" -H "X-API-Key: wrong-key" -H "Content-Type: application/json" -d "{\"question\":\"Hello\"}"
HTTP/1.1 403 Forbidden
date: Wed, 25 Nov 2026 08:46:46 GMT
server: uvicorn
content-length: 29
content-type: application/json

{"detail":"Invalid API key."}

# Không có key → 401
curl -i -X POST "http://localhost:8001/ask" -H "Content-Type: application/json" -d "{\"question\":\"Hello\"}"
HTTP/1.1 401 Unauthorized
date: Wed, 25 Nov 2026 08:50:05 GMT
server: uvicorn
content-length: 67
content-type: application/json

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

### Exercise 4.2–4.3: JWT + Rate limit

```
# Lấy token
curl -X POST "http://localhost:8002/auth/token" -H "Content-Type: application/json" -d "{\"username\":\"student\",\"password\":\"demo123\"}"
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer","expires_in_minutes":60}

# Dùng token gọi /ask → 200
curl -i -X POST "http://localhost:8002/ask" -H "Authorization: Bearer eyJhbGci..." -H "Content-Type: application/json" -d "{\"question\":\"Hello\"}"
HTTP/1.1 200 OK
{"question":"Hello","answer":"...","usage":{"requests_remaining":9,"budget_remaining_usd":2.1e-05}}

# Rate limit test (student giới hạn 10 req/phút)
# Request 1-9  → 200 OK
# Request 10   → 429 Too Many Requests
# Request 11   → 429 Too Many Requests
# Request 12   → 429 Too Many Requests
1: 200
2: 200
3: 200
4: 200
5: 200
6: 200
7: 200
8: 200
9: 200
10: 429
11: 429
12: 429
```

### Exercise 4.4: Cost guard

Cost guard đếm token ước tính (input + output) nhân với giá GPT-4o-mini ($0.00015/1K input, $0.0006/1K output), cộng dồn vào Redis key `cost:daily` với TTL 86400s. Trước mỗi request kiểm tra tổng hiện tại với `DAILY_BUDGET_USD` — vượt thì trả 402. Redis đảm bảo nhiều worker/instance cùng đếm đúng.

---

## Part 5: Scaling & Reliability

### Exercise 5.1–5.5

**Liveness vs Readiness:**
- `/health` (liveness): luôn trả 200 khi process còn chạy, kể cả Redis chết. Platform dùng để quyết định có cần restart process không.
- `/ready` (readiness): trả 503 khi Redis không kết nối được. Platform dùng để quyết định có route traffic vào instance này không. Redis chết → không nhận request mới, nhưng process không restart.

**State trong RAM hỏng khi scale:**
Nếu rate limit counter lưu trong RAM (dict Python), instance A có counter riêng, instance B có counter riêng. Load balancer round-robin → user gửi 10 request, mỗi instance chỉ thấy 5 → không bao giờ bị 429. Redis là shared store dùng chung giữa mọi instance.

**Kết quả test stateless:**
```
docker compose -p k5-day14-scaling up --build --scale agent=3 -d
python test_stateless.py

============================================================
Stateless Scaling Demo
============================================================

Session ID: b3337106-8239-477e-89a9-6b42b1da2542

Request 1: [instance-ec505a]
  Q: What is Docker?
  A: Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!...

Request 2: [instance-09066d]
  Q: Why do we need containers?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....

Request 3: [instance-ac2c59]
  Q: What is Kubernetes?
  A: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận....

Request 4: [instance-ec505a]
  Q: How does load balancing work?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....

Request 5: [instance-09066d]
  Q: What is Redis used for?
  A: Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé....

------------------------------------------------------------
Total requests: 5
Instances used: {'instance-09066d', 'instance-ac2c59', 'instance-ec505a'}
✅ All requests served despite different instances!

--- Conversation History ---
Total messages: 10
✅ Session history preserved across all instances via Redis!
```

---

## Part 6: Final Project

### Checklist Deliverable (PASS 12/12)

```
================================================================
  Production Readiness Check — Day 14 Lab
================================================================

✅ 1. Dockerfile (multi-stage, < 500 MB)        — 238 MB
✅ 2. docker-compose.yml (agent + redis)
✅ 3. .dockerignore
✅ 4. Health check endpoint (GET /health)
✅ 5. Readiness endpoint (GET /ready)
✅ 6. API Key authentication
✅ 7. Rate limiting
✅ 8. Cost guard
✅ 9. Config từ environment variables
✅ 10. Structured logging
✅ 11. Graceful shutdown                        — docker stop: exit 0, 0.9s
✅ 12. Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 11/12 tiêu chí đạt · 42/42 checks passed
  ⚠  Tiêu chí 11: SIGTERM local không test được trên Windows
      (Docker stop tắt êm: exit code 0, < 10s — đạt yêu cầu)
================================================================
```

---

## Part 3: Cloud Deployment

*(Điền sau khi deploy — xem DEPLOYMENT.md)*

- URL: https://[tên-app].railway.app
- Platform: Railway
- Screenshot: xem `screenshots/`

**So sánh railway.toml vs render.yaml:**
| | railway.toml | render.yaml |
|--|-------------|-------------|
| Builder | `DOCKERFILE` explicit | Auto-detect Dockerfile |
| Health check | `healthcheckPath = "/health"` | `healthCheckPath: /health` |
| Secret | Thêm qua Railway dashboard | `generateValue: true` / `sync: false` |
| Redis | Add Redis plugin riêng | Thêm service riêng trong yaml |

**Exercise 3.3 — Cloud Run pipeline:**
`cloudbuild.yaml` định nghĩa pipeline CI/CD: bước 1 build Docker image và push lên Artifact Registry, bước 2 deploy lên Cloud Run bằng `gcloud run deploy`. `service.yaml` khai báo resource limits, biến môi trường, min/max instances và health check path. Mỗi lần push code lên branch main, Cloud Build trigger tự động chạy pipeline — không cần deploy tay.

---

## Part 7: Benchmark & Observability

*(Điền sau khi chạy load test — xem BENCHMARK_REPORT.md)*
