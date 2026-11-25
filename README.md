# Day 14 — Deployment, Benchmark & Observability

> Đưa agent lên cloud, đo hiệu năng, và giám sát khi chạy thật.

**Sinh viên:** LuuThanhMy · **MSSV:** 2A202603532  
**AICB-P1 · VinUniversity 2026** · Hình thức: Cá nhân

---

## 🌐 Live Demo

| Endpoint | URL |
|----------|-----|
| Health check | [/health](https://k5-l3a-day14-luuthanhmy-2a202603532-deployment-b-production.up.railway.app/health) |
| API Docs | [/docs](https://k5-l3a-day14-luuthanhmy-2a202603532-deployment-b-production.up.railway.app/docs) |
| Platform | Railway (Docker + Redis) |

---

## ✅ Checklist hoàn thành

| CP | Nội dung | Kết quả |
|----|---------|---------|
| CP1 | Chạy develop app, phân tích anti-patterns | ✅ |
| CP2 | Docker build — develop **1.67 GB** vs production **240 MB** (-86%) | ✅ |
| CP3 | API Key 401/403/200, JWT + rate limit 429 | ✅ |
| CP4 | Scale 3 instance + Redis stateless — test_stateless.py pass | ✅ |
| CP5 | 06-lab-complete — 11/12 pass | ✅ |
| CP6 | Deploy Railway live | ✅ |
| CP7 | Benchmark 4 mức concurrency — BENCHMARK_REPORT.md | ✅ |
| CP8 | Grafana + Jaeger + Prometheus + Locust | ✅ |

---

## 🚀 Chạy nhanh

### Yêu cầu
```
python 3.11+
docker & docker compose
```

### 1. Chạy app develop (Part 1)
```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py
# Test: curl -X POST "http://localhost:8000/ask?question=Hello"
```

### 2. Build Docker image (Part 2)
```bash
# Build từ gốc repo
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images my-agent
```

### 3. Test API Security (Part 4)
```bash
cd 04-api-gateway/develop
set AGENT_API_KEY=secret-key-123
python app.py

# Test 401 - không có key
curl -i -X POST "http://localhost:8001/ask" -H "Content-Type: application/json" -d "{\"question\":\"Hello\"}"

# Test 200 - key đúng
curl -i -X POST "http://localhost:8001/ask" -H "X-API-Key: secret-key-123" -H "Content-Type: application/json" -d "{\"question\":\"Hello\"}"
```

### 4. Scale 3 instance (Part 5)
```bash
cd 05-scaling-reliability/production
docker compose -p k5-day14-scaling up -d --build --scale agent=3
python test_stateless.py
docker compose -p k5-day14-scaling down
```

### 5. Chạy full observability stack (Part 7)
```bash
cd 06-lab-complete/benchmark-observability/production
docker compose up -d
```

Mở trình duyệt:
- Grafana: http://localhost:3000
- Jaeger: http://localhost:16686
- Prometheus Alerts: http://localhost:9090/alerts
- Locust: http://localhost:8089

---

## 📊 Kết quả Benchmark

| Concurrency | RPS | p95 (ms) | SLO (< 500ms) |
|-------------|-----|----------|---------------|
| 1 | 7.65 | 151 | ✅ PASS |
| 5 | 7.71 | 898 | ❌ FAIL |
| 10 | 7.89 | 1554 | ❌ FAIL |
| 20 | 8.05 | 3483 | ❌ FAIL |

**Kết luận:** App develop 1 worker không scale -- RPS không tăng dù concurrency x20. Production cần multi-worker + nginx.

Xem chi tiết: [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md)

---

## 🏗️ Cấu trúc project

```
├── 01-localhost-vs-production/   # Dev vs Production gap
├── 02-docker/                    # Containerization
├── 03-cloud-deployment/          # Railway, Render, Cloud Run
├── 04-api-gateway/               # Auth, rate limiting, cost guard
├── 05-scaling-reliability/       # Stateless, Redis, Nginx LB
├── 06-lab-complete/              # Final agent (production-ready)
│   └── benchmark-observability/  # Prometheus + Grafana + Jaeger + Locust
├── utils/                        # Mock LLM dùng chung
├── MISSION_ANSWERS.md            # Câu trả lời các bài tập
├── BENCHMARK_REPORT.md           # Kết quả benchmark
└── DEPLOYMENT.md                 # Hướng dẫn deploy Railway
```

---

## 📚 Tài liệu

| File | Nội dung |
|------|---------|
| [MISSION_ANSWERS.md](MISSION_ANSWERS.md) | Trả lời toàn bộ bài tập Part 1-7 |
| [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md) | Kết quả load test 4 mức concurrency |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Hướng dẫn deploy lên Railway |
| [CHECKPOINTS.md](CHECKPOINTS.md) | Checklist chấm điểm |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Xử lý lỗi thường gặp |

---

## ⚠️ Lưu ý Windows

- Dùng **cmd** (không phải PowerShell) để chạy curl
- Chạy `chcp 65001` trước để hiển thị tiếng Việt đúng
- SIGTERM không test được trên Windows -- tiêu chí 11 dùng `docker stop` để verify (exit code 0, < 10s)
- Build Docker image từ **gốc repo**, không cd vào thư mục con
