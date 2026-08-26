# Failure Cluster Analysis — Phase A

**Sinh viên:** Hoàng Trọng Đại
**Ngày:** 2026-08-26

---

## 1. Aggregate RAGAS Scores theo Distribution

| Metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | 0.9833 | 0.5151 | 0.7000 |
| answer_relevancy | 0.8542 | 0.7526 | 0.6073 |
| context_precision | 0.9375 | 0.9667 | 0.9833 |
| context_recall | 0.8750 | 0.8333 | 0.6833 |
| **avg_score** | **0.9125** | **0.7669** | **0.7435** |

(count: factual=20, multi_hop=20, adversarial=10 — tổng 50 câu, đúng phân bố yêu cầu)

---

## 2. Bottom 10 Questions

| Rank | Distribution | Question | avg_score | worst_metric |
|---|---|---|---|---|
| 1 | multi_hop | Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào? | 0.375 | faithfulness |
| 2 | multi_hop | Nhân viên Manager có thâm niên 12 năm: tổng phụ cấp hàng tháng và số ngày phép năm theo v2024 là bao nhiêu? | 0.375 | faithfulness |
| 3 | adversarial | Nhân viên thử việc có được nghỉ phép năm không? | 0.4167 | faithfulness |
| 4 | adversarial | Nhân viên thử việc có được hưởng bảo hiểm sức khỏe PVI không? | 0.4167 | faithfulness |
| 5 | adversarial | Nhân viên Manager có thể dùng VPN cá nhân (như NordVPN) khi WFH để tăng bảo mật thêm không? | 0.4167 | faithfulness |
| 6 | factual | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | 0.5768 | context_recall |
| 7 | multi_hop | Nhân viên tạm ứng 15 triệu, sau 20 ngày mới thanh toán. Bị phạt bao nhiêu? | 0.6373 | faithfulness |
| 8 | multi_hop | Nhân viên tạm ứng 4 triệu và một nhân viên khác tạm ứng 7 triệu: quy trình phê duyệt khác nhau thế nào? | 0.6741 | faithfulness |
| 9 | multi_hop | Nhân viên đi công tác trong nước 2 ngày, ở khách sạn giá 1.500.000 VNĐ/đêm. Công ty thanh toán tối đa bao nhiêu cho tiền khách sạn? | 0.689 | faithfulness |
| 10 | multi_hop | Lương thử việc của nhân viên Junior mức cao nhất là bao nhiêu? | 0.706 | faithfulness |

Nhận xét nhanh: 9/10 câu tệ nhất có `worst_metric = faithfulness`, và phân bố là 6 `multi_hop` + 3 `adversarial` + 1 `factual`. Không có câu `factual` "thuần" (không tính toán) nào lọt vào bottom 10 vì trả lời — chỉ có 1 câu `factual` duy nhất (#6, do thiếu chunk chứa ngưỡng phê duyệt 50 triệu → context_recall thấp).

---

## 3. Failure Cluster Matrix

*(Mỗi ô = số câu có worst_metric = row, thuộc distribution = col)*

| worst_metric | factual | multi_hop | adversarial | Total |
|---|---|---|---|---|
| faithfulness | 1 | 14 | 3 | 18 |
| answer_relevancy | 14 | 4 | 1 | 19 |
| context_precision | 1 | 1 | 0 | 2 |
| context_recall | 4 | 1 | 6 | 11 |
| **Total (= count)** | **20** | **20** | **10** | **50** |

---

## 4. Dominant Failure Analysis

**Dominant distribution (theo `cluster_analysis()`):** `factual`
**Dominant metric (theo `cluster_analysis()`):** `answer_relevancy`

**Lý do phân tích — và một lưu ý quan trọng về cách tính:**

`cluster_analysis()` chọn `dominant_failure_distribution` bằng cách so tổng theo cột của matrix — nhưng tổng mỗi cột **chính là số câu của distribution đó** (mỗi câu chỉ có đúng 1 `worst_metric` nên luôn cộng dồn về đúng count của group). Vì `factual` và `multi_hop` đều có 20 câu (hòa), hàm `max()` trả về phần tử đầu tiên gặp trong list `["factual","multi_hop","adversarial"]` → luôn là `factual` bất kể chất lượng thực tế. Đây là điểm yếu của thước đo "dominant distribution" khi các nhóm có cỡ mẫu bằng nhau — nó đo "nhóm nào đông câu nhất", không phải "nhóm nào yếu nhất".

Nhìn vào **avg_score thực tế** (bảng mục 1) thì bức tranh ngược lại: `factual` mạnh nhất (0.9125), còn `adversarial` (0.7435) và `multi_hop` (0.7669) mới là 2 nhóm yếu. Trong đó `multi_hop` sụp chủ yếu ở `faithfulness` (0.515) — mô hình phải tự tính toán/kết hợp số liệu từ nhiều tài liệu (lương theo cấp bậc + thâm niên, phạt tạm ứng theo ngày trễ hạn, hạn mức khách sạn công tác...) và thường bịa hoặc tính sai con số, dù bối cảnh retrieval (context_precision=0.967) lại rất tốt — tức là **lỗi nằm ở khâu generation/reasoning, không phải retrieval**.

Về `answer_relevancy` là metric "dominant" theo count (19/50 câu, nhỉnh hơn faithfulness 18/50): đây là hệ quả phụ của corpus HR tiếng Việt có nhiều tài liệu policy trùng chủ đề nhưng khác version (v2023/v2024, v1/v2) — câu trả lời dù đúng nội dung một phiên bản nào đó vẫn có thể bị RAGAS chấm answer_relevancy thấp nếu nó không khớp sát với đúng câu hỏi (ví dụ trả lời cả hai phiên bản, hoặc trả lời phiên bản không được hỏi).

---

## 5. Suggested Fixes

| Metric yếu | Root cause | Suggested fix |
|---|---|---|
| faithfulness | LLM hallucinating, đặc biệt khi phải tính toán số liệu multi-hop (lương, phụ cấp, phạt) | Tighten system prompt (yêu cầu show working / trích rõ số liệu từ context trước khi tính), lower temperature, thêm bước verify phép tính bằng code thay vì để LLM tự nhẩm |
| context_recall | Thiếu chunk liên quan — đặc biệt `adversarial` (0.683) khi câu hỏi cố tình mập mờ giữa các version policy | Cải thiện chunking (đảm bảo mỗi version policy là 1 chunk riêng, có metadata version rõ ràng) hoặc thêm BM25/keyword filter theo version |
| context_precision | Quá nhiều chunk không liên quan lẫn vào — ít gặp nhất ở dataset này (2/50 câu) | Thêm reranking mạnh hơn hoặc metadata filter (đã tương đối tốt, ưu tiên thấp) |
| answer_relevancy | Câu trả lời không khớp sát câu hỏi — đặc biệt `factual` (14/20 câu) do nhầm lẫn version policy | Improve prompt template: yêu cầu LLM xác định rõ "câu hỏi đang hỏi về version nào" trước khi trả lời, chỉ trả lời đúng version được hỏi |

---

## 6. Nhận xét về Adversarial Distribution

So sánh avg_score: `adversarial` (0.7435) < `factual` (0.9125) — **đạt điều kiện bonus Phase A** (+4 điểm, "Adversarial avg_score < factual avg_score"). Điều này đúng như kỳ vọng: bộ 10 câu adversarial được thiết kế để "bẫy" pipeline bằng version conflict (v2023 vs v2024) và câu hỏi phủ định/mập mờ, và pipeline đã thực sự bị nhầm ở mức đáng kể.

3/10 câu adversarial rơi vào bottom 10 (rank #3, #4, #5 — đều avg_score=0.4167, đều `worst_metric=faithfulness`):
- "Nhân viên thử việc có được nghỉ phép năm không?" — mô hình có thể trả lời mơ hồ hoặc sai vì corpus có nhiều tài liệu liên quan (nghỉ phép v2023/v2024, thử việc) dễ gây nhầm lẫn.
- "Nhân viên thử việc có được hưởng bảo hiểm sức khỏe PVI không?" — tương tự, cần phân biệt rõ quyền lợi nhân viên chính thức vs thử việc.
- "Nhân viên Manager có thể dùng VPN cá nhân (như NordVPN) khi WFH để tăng bảo mật thêm không?" — câu hỏi dạng "có nên tự ý làm X không" dễ khiến mô hình trả lời "được" một cách hời hợt thay vì tra đúng chính sách cấm VPN cá nhân.

Ngoài ra, câu #41 trong `human_labels_10q.json` ("Nhân viên được nghỉ bao nhiêu ngày phép năm?" trả lời theo v2023 đã hết hiệu lực) cũng minh hoạ đúng lỗi version-conflict mà bộ test adversarial nhắm tới, dù câu này không nằm trong bottom-10 của Phase A (nó thuộc distribution `factual` trong test_set_50q.json, không phải `adversarial`) — cho thấy lỗi nhầm version không chỉ giới hạn ở nhóm câu hỏi được gắn nhãn adversarial mà lan cả sang factual.
