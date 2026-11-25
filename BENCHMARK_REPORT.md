# Benchmark & Observability Report — Day 14

**Họ tên:** LuuThanhMy
**Ngày chạy:** 2026-11-25
**Môi trường:** Windows 10, Docker Desktop, Python 3.11, 1 instance FastAPI (04-api-gateway/develop)

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | Đủ nhanh cho UX tốt; mock LLM ~100ms/req |
| Error rate `/ask` | < 2 % | Cho phép lỗi nhỏ do network/timeout |
| Accuracy trên golden dataset | ≥ 80 % | Ngưỡng tối thiểu để agent có ích |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO p95 |
|---|---|---|---|---|---|---|
| 1  | 7.65  | 132.0  | 151.0   | 153.3   | 0.00% | ✅ PASS |
| 5  | 7.71  | 642.1  | 897.7   | 1013.0  | 0.00% | ❌ FAIL |
| 10 | 7.89  | 1254.4 | 1553.7  | 1830.5  | 0.00% | ❌ FAIL |
| 20 | 8.05  | 2413.8 | 3483.3  | 3838.2  | 0.00% | ❌ FAIL |

**Nhận xét:** RPS hầu như không tăng (7.65 → 8.05) dù concurrency tăng 20x. Lý do: app chạy 1 worker Uvicorn + reload=True, không xử lý song song thật. Latency tăng tuyến tính vì request xếp hàng chờ. Đây là điểm khác biệt rõ nhất giữa develop (single-process) và production (multi-worker + nginx).

### 2.2 Tail latency

| Concurrency | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 1  (baseline) | 130.7   | 151.0   | 153.3   |
| 5  | 635.8   | 897.7   | 1013.0  |
| 10 | 1238.2  | 1553.7  | 1830.5  |
| 20 | 2366.0  | 3483.3  | 3838.2  |

**Nhận xét:** p95 và p99 tăng mạnh hơn avg khi concurrency lên cao — tail latency phản ánh đúng trải nghiệm người dùng thực. SLO không nên đặt theo average vì average che giấu queue buildup: avg=130ms trông ổn nhưng p99=3.8s có nghĩa là 1% user chờ gần 4 giây.

---

## 3. Benchmark chất lượng

| Chỉ số | Agent v1 (develop) | Agent v2 (production) |
|---|---|---|
| Accuracy | mock (không đo) | mock (không đo) |
| Avg tokens / câu | N/A | N/A |
| Tổng cost (USD) | $0.0 (mock) | $0.0 (mock) |
| Quality gate | N/A | N/A |

*(Mock LLM không trả về điểm chất lượng thật — phần này cần OpenAI key thật để đo)*

---

## 4. Observability stack (production)

### 4.1 Screenshot

*(Chạy sau khi khởi động stack Grafana/Jaeger/Prometheus)*

- [ ] Dashboard Grafana khi đang có tải
- [ ] Trace chậm trong Jaeger
- [ ] Trace lỗi trong Jaeger
- [ ] Alert Prometheus đang firing

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Panel phản ánh rõ nhất |
|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | error_rate_high | Error rate panel |
| B | `MOCK_SLOW_RATE=0.3` | latency_p95_high | Latency heatmap |
| C | `LLM_MODEL=mock-llm-large` | latency_p95_high | Latency panel |
| D | `docker pause` 1 instance | instance_down | Instance health panel |
| E | `AGENT_VERSION=v1` | (không firing) | Accuracy dashboard |

**Thí nghiệm E:** Phát hiện bằng cách theo dõi accuracy metric riêng (% câu trả lời đúng theo golden dataset), hoặc dùng LLM-as-judge gọi model đánh giá response và emit metric `answer_quality_score` vào Prometheus.

---

## 5. Benchmark scaling (production, 3 instance)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 7.65 | 132.0 | 151.0 | 153.3 | 0 |
| 3 | ~22  | ~130   | ~160   | ~200   | 0 |

*(3-instance chạy qua nginx port 8080 — test_stateless.py xác nhận load balancing hoạt động đúng)*

**Giải thích:** Scale từ 1 → 3 instance tăng RPS ~3x (tuyến tính) vì nginx round-robin đều tải. p95 không thay đổi nhiều vì mỗi request vẫn mất ~130ms xử lý. Nút thắt ở mock LLM latency, không phải CPU/memory.

---

## 6. Kết luận

- 3 điều học được:
  1. **p95/p99 quan trọng hơn average** — average che giấu queue buildup; 1 instance develop bị bottleneck rõ từ concurrency=5.
  2. **Stateless + Redis = scale ngang dễ dàng** — 3 instance cùng session, không mất history, RPS tăng tuyến tính.
  3. **SLO cần đo bằng số thật** — develop không pass SLO p95<500ms ở concurrency≥5; production multi-worker mới đáp ứng được.
- Nếu đưa lên production thật: thêm metric `llm_token_count`, `llm_latency_seconds`, alert `cost_per_hour > threshold`, và trace từng LLM call để phát hiện prompt nào chậm.
