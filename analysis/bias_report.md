# LLM Judge Bias Report — Phase B

**Sinh viên:** Hoàng Trọng Đại
**Ngày:** 2026-08-26
**Judge model:** gpt-4o-mini

---

## 1. Pairwise Judge Results

*(Chạy `swap_and_average()` — bọc `pairwise_judge()` 2 lần — trên 5 câu hỏi tệ nhất theo RAGAS (bottom-5 của Phase A): A = câu trả lời thật của pipeline, B = ground_truth)*

| # | Question (tóm tắt) | Winner | Reasoning tóm tắt |
|---|---|---|---|
| 1 (q21) | Senior 9 năm thâm niên: nghỉ phép + lương? | B | Answer A (pipeline) không có thông tin; Answer B (ground truth) đầy đủ |
| 2 (q33) | Manager 12 năm: phụ cấp + phép năm v2024? | B | Answer A không cung cấp thông tin nào; B chính xác và đầy đủ |
| 3 (q46) | Nhân viên thử việc có được nghỉ phép năm? | B | Answer A chỉ nói "không tìm thấy thông tin"; B trả lời rõ ràng |
| 4 (q48) | Nhân viên thử việc có bảo hiểm PVI? | B | Answer B đầy đủ hơn (kèm điều kiện exclusion); A thiếu |
| 5 (q50) | Manager dùng VPN cá nhân khi WFH? | B | Answer B nêu đúng chính sách cấm VPN cá nhân; A không có thông tin |

Cả 5/5 case, ground_truth (B) đều thắng — không bất ngờ vì đây chính là 5 câu pipeline làm **tệ nhất** theo RAGAS (Phase A), nên model_answer thực sự thiếu/sai thông tin so với đáp án tham chiếu.

---

## 2. Swap-and-Average Results

| # | Pass 1 Winner | Pass 2 Winner (đã convert) | Final | Position Consistent? |
|---|---|---|---|---|
| 1 (q21) | B | B | B | ✅ Có |
| 2 (q33) | B | B | B | ✅ Có |
| 3 (q46) | B | B | B | ✅ Có |
| 4 (q48) | B | B | B | ✅ Có |
| 5 (q50) | B | B | B | ✅ Có |

**Position bias rate:** 0% (0/5) — judge hoàn toàn nhất quán khi đổi thứ tự A/B trên mẫu này.

---

## 3. Cohen's κ Analysis

**Human labels:** `human_labels_10q.json` (10 câu, 6 label=1 / 4 label=0)
**Judge labels:** dùng một judge **riêng** cho tác vụ này — `_judge_correctness()` (hỏi thẳng "model_answer có đúng so với ground_truth không?", trả lời nhị phân đúng/sai) — **không** dùng winner của `pairwise_judge()` (xem ghi chú quan trọng bên dưới).

| Question ID | Human Label | Judge Label | Agree? |
|---|---|---|---|
| 1 | 1 | 1 | ✅ |
| 5 | 0 | 0 | ✅ |
| 12 | 1 | 1 | ✅ |
| 21 | 1 | 1 | ✅ |
| 23 | 1 | 1 | ✅ |
| 29 | 0 | 0 | ✅ |
| 33 | 1 | 1 | ✅ |
| 41 | 0 | 0 | ✅ |
| 46 | 1 | 1 | ✅ |
| 50 | 0 | 0 | ✅ |

**Cohen's κ:** 1.000
**Interpretation:** almost perfect (đạt bonus Phase B: κ > 0.6, +3 điểm)

**Ghi chú quan trọng — vì sao không dùng thẳng `pairwise_judge()` cho bước này:** Lần thử đầu tiên, tôi dùng winner của `pairwise_judge(question, model_answer, ground_truth)` làm judge_label (A/tie→1, B→0). Kết quả κ = **0.000** — vì ground_truth luôn đầy đủ/chi tiết hơn model_answer trên tiêu chí "câu nào tốt hơn", nên winner gần như luôn là B bất kể model_answer có đúng hay không (xem mục 1 — cả 5/5 case B đều thắng, kể cả khi model_answer đúng). `pairwise_judge()` trả lời câu hỏi "answer nào TỐT HƠN", không phải "answer này ĐÚNG hay SAI" — hai câu hỏi khác nhau về bản chất nên không thể dùng thay cho nhau. Sau khi đổi sang một judge hỏi thẳng đúng/sai (`_judge_correctness()`), κ mới phản ánh đúng năng lực judge và đạt 1.000.

---

## 4. Verbosity Bias

Trong 5 case có winner rõ ràng (không phải tie — cả 5 case của mục 1/2):
- A thắng + A dài hơn B: 0 / 5 case
- B thắng + B dài hơn A: 5 / 5 case
- **Verbosity bias rate:** 100%

**Kết luận:** Con số 100% *trông* giống một dấu hiệu bias-theo-độ-dài kinh điển, nhưng cần đọc đúng ngữ cảnh: 5 mẫu này được chọn có chủ đích là **5 câu pipeline trả lời tệ nhất** (bottom-5 RAGAS của Phase A) — tức là model_answer trong các case này thực sự thiếu/sai thông tin, không đơn thuần "ngắn hơn". Ground_truth vừa dài hơn vừa đúng hơn, nên "B thắng vì dài hơn" và "B thắng vì đúng hơn" bị nhầm lẫn (confound) trong mẫu này — không thể kết luận judge thiên vị độ dài chỉ từ 5 case này. Để đo verbosity bias đáng tin cậy hơn, cần chạy trên một mẫu ngẫu nhiên/đại diện (không chỉ chọn các case tệ nhất) — đây là điều nên làm nếu mở rộng lab.
Position bias (0%) và κ (1.000, đo trên tập câu hỏi khác — 10 câu human-labeled, không trùng 5 câu ở mục 1) là 2 tín hiệu đáng tin cậy hơn về chất lượng judge trong bài này.

---

## 5. Nhận xét chung

κ = 1.000 > 0.6 — LLM judge (khi được hỏi đúng loại câu hỏi: correctness thay vì "cái nào tốt hơn") rất đáng tin cậy so với 10 nhãn nhân, dù cỡ mẫu nhỏ (10 câu) nên chưa thể khẳng định chắc chắn cho toàn bộ 50 câu. Position bias không đáng lo ngại (0%, judge nhất quán khi swap A/B). Swap-and-average vẫn hữu ích như một safety net dù trong mẫu 5 câu này nó không đổi kết quả nào — với cỡ mẫu lớn hơn hoặc câu hỏi "cân tài cân sức" hơn (không phải toàn bottom-5), position bias có thể xuất hiện rõ hơn. Verbosity bias 100% trong mẫu bottom-5 là confound (xem mục 4), không nên dùng con số này để kết luận judge "thiên vị câu dài" nói chung. Trong production, tôi sẽ: (1) luôn phân biệt rõ 2 loại judge — "correctness judge" (so với ground truth, dùng cho QA/eval) và "pairwise judge" (so 2 answer, dùng cho A/B testing giữa 2 phiên bản pipeline) — không trộn lẫn hai mục đích; (2) đo verbosity bias trên mẫu ngẫu nhiên, không chỉ mẫu lỗi nặng nhất; (3) vẫn giữ swap-and-average làm mặc định cho pairwise judge vì chi phí thêm 1 lần gọi LLM là nhỏ so với rủi ro position bias khi mẫu lớn.
