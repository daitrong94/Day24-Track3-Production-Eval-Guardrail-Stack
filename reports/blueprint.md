# CI/CD Blueprint: RAG Eval + Guardrail Stack

**Sinh viên:** Hoàng Trọng Đại
**Ngày:** 2026-08-26

---

## Guard Stack Architecture

```
User Input
    │
    ▼ (~11ms P95)
[Presidio PII Scan]
    │ block if: VN_CCCD / VN_PHONE / EMAIL detected
    │ action:   return 400 + "PII detected in query"
    ▼ (~5147ms P95 — xem ghi chú cold-start bên dưới)
[NeMo Input Rail]
    │ block if: off-topic / jailbreak / prompt injection
    │ action:   return 503 + refuse message
    ▼
[RAG Pipeline (Day 18)]
    │ M1 Chunk → M2 Search → M3 Rerank → GPT-4o-mini
    │ (~12.9s/câu trung bình đo được khi generate answers_50q.json — xem ghi chú)
    ▼
[NeMo Output Rail]
    │ flag if:  PII / thông tin nhạy cảm (mật khẩu, CCCD, SĐT cá nhân) trong response
    │ action:   thay bằng safe response ("Tôi không thể cung cấp thông tin này...")
    ▼
User Response
```

---

## Latency Budget

*(Đo bằng `measure_p95_latency()` trên 10 adversarial inputs, n_runs=10; RAG Pipeline đo gián tiếp từ `setup_answers.py` chạy 50 câu qua Day 18 pipeline)*

| Layer | P50 (ms) | P95 (ms) | P99 (ms) | Budget |
|---|---|---|---|---|
| Presidio PII | 7.17 | 10.66 | 10.66 | <10ms |
| NeMo Input Rail | 18.71 | 5146.80 | 5146.80 | <300ms |
| RAG Pipeline | ~12,900 (trung bình/câu, chưa đo P95 riêng) | — | — | <2000ms |
| NeMo Output Rail | *(chưa đo riêng — Task 12 chỉ yêu cầu đo Presidio + NeMo input)* | — | — | <300ms |
| **Total Guard (Presidio + NeMo input)** | 25.88 | **5153.56** | 5153.56 | **<500ms** |

**Budget OK?** [x] No

**Comment:** NeMo input rail là bottleneck tuyệt đối — P50 (18.71ms) thực ra rất nhanh vì các check (jailbreak/off-topic/PII-request/prompt-injection) đã được viết lại thành `execute <action>()` bằng keyword-matching Python thuần (xem `guardrails/actions.py`), không gọi LLM. Nhưng P95/P99 lại vọt lên ~5.1s — đây gần như chắc chắn là **cold-start** của lần gọi `generate_async()` đầu tiên trong loạt đo (load config Colang + compile flows), vì n_runs=10 nên percentile thứ 95/99 rơi đúng vào phần tử lớn nhất (outlier duy nhất). Trong production, cách tối ưu là giữ một `LLMRails` instance đã warm-up sẵn (singleton, load 1 lần lúc khởi động service) thay vì khởi tạo mới mỗi request — điều này áp dụng y hệt cho `run_adversarial_suite()`/`measure_p95_latency()` đã được sửa để tái dùng 1 `rails` object cho toàn bộ batch thay vì tạo mới ở mỗi lần gọi `check_input_rail()`.
RAG Pipeline (M1→M2→M3→GPT-4o-mini) cũng vượt xa budget rất nhiều (~12.9s/câu đo được thực tế khi chạy `setup_answers.py` trên 50 câu, tổng 644s/50 câu) — chậm hơn cả NeMo, chủ yếu do load model (BGE-M3 embedding, cross-encoder reranker) và gọi GPT-4o-mini tuần tự cho từng câu, không có warm cache/connection pooling hay batch inference.

---

## CI/CD Gates (phải pass trước khi merge to main)

```yaml
# .github/workflows/rag_eval.yml
- name: RAGAS Quality Gate
  run: python src/phase_a_ragas.py
  env:
    MIN_FAITHFULNESS: 0.75
    MIN_AVG_SCORE: 0.65

- name: Guardrail Gate
  run: pytest tests/test_phase_c.py -k "test_adversarial_suite_pass_rate"
  # phải ≥ 15/20 (75%)

- name: Latency Gate
  run: python -c "from src.phase_c_guard import measure_p95_latency; ..."
  # P95 total < 500ms
```

**Kết quả chạy thật với 3 gates trên:**

| Gate | Ngưỡng | Đo được | Pass? |
|---|---|---|---|
| RAGAS faithfulness (50q) | ≥ 0.75 | 0.7394 (weighted avg) | ❌ FAIL — dưới ngưỡng, chủ yếu do `multi_hop` (0.515) kéo xuống |
| RAGAS avg_score (50q) | ≥ 0.65 (MIN_AVG_SCORE) | 0.8205 | ✅ PASS |
| Adversarial suite pass rate | ≥ 75% (15/20) | 100% (20/20) | ✅ PASS (đạt luôn bonus ≥90%) |
| P95 total guard latency | < 500ms | 5,153.56ms | ❌ FAIL — do cold-start NeMo, xem phần Latency Budget |

→ Với ngưỡng CI thật, pipeline **sẽ bị chặn merge** vì faithfulness gate và latency gate đều fail — đúng như mục đích của CI gate (bắt được vấn đề thật trước khi lên production).

---

## Monitoring Dashboard (production)

| Metric | Alert Threshold | Action |
|---|---|---|
| RAGAS faithfulness (daily sample) | < 0.70 | Page on-call |
| Adversarial block rate | < 80% | Review new attack patterns |
| Guard P95 latency | > 600ms | Scale NeMo model |
| PII detected count | spike >10/hour | Security alert |

---

## Kết quả thực tế từ Lab

| | Kết quả |
|---|---|
| RAGAS avg_score (50q) | 0.8205 |
| RAGAS faithfulness (50q, weighted) | 0.7394 (< 0.75 gate) |
| Worst metric | `answer_relevancy` (worst-metric-count cao nhất: 19/50 câu) — nhưng `faithfulness` mới là metric có **giá trị tuyệt đối thấp nhất** ở `multi_hop` (0.515) và `adversarial` (0.7), xem `analysis/failure_clusters.md` |
| Dominant failure distribution | `factual` (theo `cluster_analysis()`) — **lưu ý**: đây là artifact của cách tính (tổng theo cột = số câu trong distribution, factual/multi_hop đều có 20 câu nên hòa, tie-break chọn phần tử đầu tiên trong list); xét theo avg_score thực tế thì `adversarial` (0.7435) và `multi_hop` (0.7669) mới là 2 distribution yếu nhất, không phải `factual` (0.9125 — cao nhất!) |
| Cohen's κ | 1.000 (almost perfect — đạt bonus κ>0.6) |
| Adversarial pass rate | 20 / 20 (100% — đạt bonus ≥18/20) |
| Guard P95 latency | 5,153.56 ms (Presidio + NeMo input; vượt budget 500ms — xem ghi chú cold-start) |

---

## Nhận xét & Cải tiến

Pipeline hoạt động tốt trên câu hỏi đơn giản (`factual` đạt avg_score 0.9125, faithfulness 0.983) và guardrail chặn được 100% adversarial suite kể cả jailbreak/prompt-injection/off-topic/PII — cho thấy tầng Presidio + NeMo input rail (viết lại bằng `execute action()` thay vì canonical-form matching) hoạt động đáng tin cậy. Điểm yếu rõ nhất là `faithfulness` trên câu `multi_hop` (0.515) — pipeline hay bịa số liệu khi phải tính toán/kết hợp nhiều tài liệu (lương, phụ cấp, phạt tạm ứng), và `adversarial` yếu ở cả `faithfulness` (0.7) lẫn `context_recall` (0.683) — đúng như thiết kế bài test, pipeline hay bị nhầm giữa policy v2023/v2024. LLM-judge (κ=1.000 so với 10 human label) cho thấy có thể tin cậy judge này để tự động hoá review ở quy mô lớn hơn 10 câu, dù cần lưu ý rằng correctness-judge (so sánh model_answer với ground_truth) khác với pairwise judge (so sánh 2 answer) — dùng nhầm loại judge sẽ cho κ vô nghĩa (đã gặp phải khi thử dùng winner của pairwise_judge làm nhãn đúng/sai, ground_truth luôn "thắng" nên κ=0). Nếu deploy production thật, tôi sẽ: (1) thêm bước re-generation/self-correction khi RAGAS faithfulness thấp cho câu multi-hop thay vì trả thẳng câu trả lời hallucinate, (2) giữ 1 `LLMRails` instance warm thay vì khởi tạo mới mỗi request để loại bỏ cold-start ~5s, và (3) tối ưu RAG pipeline (batch embedding, cache reranker) vì hiện tại ~12.9s/câu là không chấp nhận được cho production dù guardrail có nhanh cỡ nào.
