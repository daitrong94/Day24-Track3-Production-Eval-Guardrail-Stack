from __future__ import annotations

"""Phase B: LLM-as-Judge — pairwise, swap-and-average, Cohen κ, bias analysis."""

import json
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, JUDGE_MODEL, HUMAN_LABELS_PATH, ANSWERS_PATH, TEST_SET_PATH

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class JudgeResult:
    question: str
    answer_a: str
    answer_b: str
    winner_pass1: str       # "A" | "B" | "tie"  (original order)
    winner_pass2: str       # "A" | "B" | "tie"  (after swap, ALREADY converted back)
    final_winner: str       # consensus after swap-and-average
    reasoning_pass1: str
    reasoning_pass2: str
    position_consistent: bool  # True if both passes agree on same answer
    scores_pass1: dict = field(default_factory=dict)  # {"A": float, "B": float}
    scores_pass2: dict = field(default_factory=dict)


# ─── Task 5: Pairwise Judge ───────────────────────────────────────────────────

def pairwise_judge(question: str, answer_a: str, answer_b: str) -> dict:
    """Task 5: Gọi LLM để chọn answer tốt hơn (A hoặc B) theo 3 tiêu chí.

    Tiêu chí đánh giá:
        - Độ chính xác (accuracy): có khớp với thực tế chính sách không?
        - Độ đầy đủ (completeness): có trả lời đủ câu hỏi không?
        - Tính súc tích (conciseness): có thừa / thiếu thông tin không?

    Returns:
        {"winner": "A"|"B"|"tie", "reasoning": str, "scores": {"A": float, "B": float}}
    """
    # HƯỚNG DẪN GỐC (đã implement bên dưới): Task 5 - Pairwise judge
    # PROMPT_TEMPLATE = '''Bạn là một expert đánh giá chất lượng câu trả lời RAG.
    #
    # Câu hỏi: {question}
    #
    # Answer A:
    # {answer_a}
    #
    # Answer B:
    # {answer_b}
    #
    # Đánh giá dựa trên 3 tiêu chí: độ chính xác, đầy đủ, súc tích.
    # Trả lời JSON (chỉ JSON, không text khác):
    # {{"winner": "A" hoặc "B" hoặc "tie", "reasoning": "giải thích ngắn gọn", "scores": {{"A": 0.0-1.0, "B": 0.0-1.0}}}}
    # '''
    #
    # from openai import OpenAI
    # client = OpenAI()
    # resp = client.chat.completions.create(
    #     model=JUDGE_MODEL,
    #     messages=[
    #         {"role": "system", "content": "Bạn là expert đánh giá RAG. Chỉ trả lời JSON."},
    #         {"role": "user",   "content": PROMPT_TEMPLATE.format(
    #             question=question, answer_a=answer_a, answer_b=answer_b)},
    #     ],
    #     response_format={"type": "json_object"},
    # )
    # return json.loads(resp.choices[0].message.content)
    PROMPT_TEMPLATE = '''Bạn là một expert đánh giá chất lượng câu trả lời RAG.

Câu hỏi: {question}

Answer A:
{answer_a}

Answer B:
{answer_b}

Đánh giá dựa trên 3 tiêu chí: độ chính xác, đầy đủ, súc tích.
Trả lời JSON (chỉ JSON, không text khác):
{{"winner": "A" hoặc "B" hoặc "tie", "reasoning": "giải thích ngắn gọn", "scores": {{"A": 0.0-1.0, "B": 0.0-1.0}}}}
'''

    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": "Bạn là expert đánh giá RAG. Chỉ trả lời JSON."},
            {"role": "user",   "content": PROMPT_TEMPLATE.format(
                question=question, answer_a=answer_a, answer_b=answer_b)},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


# ─── Task 6: Swap-and-Average ─────────────────────────────────────────────────

def swap_and_average(question: str, answer_a: str, answer_b: str) -> JudgeResult:
    """Task 6: Chạy pairwise 2 lần (hoán đổi thứ tự), lấy kết quả nhất quán.

    Lý do: LLM thường có position bias (ưu tiên answer xuất hiện trước).
    Bằng cách swap, ta phát hiện và giảm bias này.

    Logic:
        Pass 1: judge(q, A, B) → winner_1 (trong không gian A/B)
        Pass 2: judge(q, B, A) → winner_2_raw (trong không gian B/A)
        Convert: nếu winner_2_raw="A" thì thực ra là B (vì đã swap)
        Final:   nếu winner_1 == winner_2 → final = winner_1
                 nếu khác nhau → final = "tie"
    """
    # HƯỚNG DẪN GỐC (đã implement bên dưới): Task 6 - Swap-and-average
    # pass1 = pairwise_judge(question, answer_a, answer_b)
    # pass2_raw = pairwise_judge(question, answer_b, answer_a)  # SWAP!
    #
    # # Convert pass2 back to original A/B space
    # swap_map = {"A": "B", "B": "A", "tie": "tie"}
    # winner_pass2 = swap_map[pass2_raw["winner"]]
    #
    # # Average: consensus only if both agree
    # if pass1["winner"] == winner_pass2:
    #     final = pass1["winner"]
    # else:
    #     final = "tie"  # disagreement = inconclusive
    #
    # position_consistent = (pass1["winner"] == winner_pass2)
    #
    # return JudgeResult(
    #     question=question, answer_a=answer_a, answer_b=answer_b,
    #     winner_pass1=pass1["winner"], winner_pass2=winner_pass2,
    #     final_winner=final,
    #     reasoning_pass1=pass1["reasoning"], reasoning_pass2=pass2_raw["reasoning"],
    #     position_consistent=position_consistent,
    #     scores_pass1=pass1["scores"],
    #     scores_pass2={"A": pass2_raw["scores"]["B"], "B": pass2_raw["scores"]["A"]},
    # )
    pass1 = pairwise_judge(question, answer_a, answer_b)
    pass2_raw = pairwise_judge(question, answer_b, answer_a)

    swap_map = {"A": "B", "B": "A", "tie": "tie"}
    winner_pass2 = swap_map[pass2_raw["winner"]]

    if pass1["winner"] == winner_pass2:
        final = pass1["winner"]
    else:
        final = "tie"

    position_consistent = (pass1["winner"] == winner_pass2)

    return JudgeResult(
        question=question, answer_a=answer_a, answer_b=answer_b,
        winner_pass1=pass1["winner"], winner_pass2=winner_pass2,
        final_winner=final,
        reasoning_pass1=pass1["reasoning"], reasoning_pass2=pass2_raw["reasoning"],
        position_consistent=position_consistent,
        scores_pass1=pass1["scores"],
        scores_pass2={"A": pass2_raw["scores"]["B"], "B": pass2_raw["scores"]["A"]},
    )


# ─── Task 7: Cohen's κ ────────────────────────────────────────────────────────

def cohen_kappa(judge_labels: list[int], human_labels: list[int]) -> float:
    """Task 7: Tính Cohen's κ giữa LLM judge và human labels.

    Args:
        judge_labels:  nhãn từ LLM judge (0 = bad answer, 1 = good answer)
        human_labels:  nhãn từ human_labels_10q.json

    Returns:
        κ ∈ [-1, 1]
        Thang đo Landis-Koch: <0=poor, 0-0.2=slight, 0.2-0.4=fair,
                               0.4-0.6=moderate, 0.6-0.8=substantial, 0.8-1=almost perfect

    Gợi ý A — dùng scikit-learn:
        from sklearn.metrics import cohen_kappa_score
        return cohen_kappa_score(human_labels, judge_labels)

    Gợi ý B — tính tay:
        n = len(judge_labels)
        p_o = sum(j == h for j, h in zip(judge_labels, human_labels)) / n
        p_e = (judge_labels.count(1)/n * human_labels.count(1)/n +
               judge_labels.count(0)/n * human_labels.count(0)/n)
        κ = (p_o - p_e) / (1 - p_e) if p_e != 1 else 0
        return κ
    """
    # HƯỚNG DẪN GỐC (đã implement bên dưới): Task 7 - dùng Gợi ý A (scikit-learn)
    from sklearn.metrics import cohen_kappa_score
    return float(cohen_kappa_score(human_labels, judge_labels))


# ─── Task 8: Bias Report ──────────────────────────────────────────────────────

def bias_report(judge_results: list[JudgeResult]) -> dict:
    """Task 8: Đo lường position bias và verbosity bias.

    Position bias: LLM chọn answer theo vị trí (A hay B) thay vì chất lượng.
        → Đo bằng % cases where position_consistent = False

    Verbosity bias: LLM ưu tiên answer dài hơn dù không chính xác hơn.
        → Đo bằng: trong các case A thắng, A có dài hơn B không? Tương tự cho B.

    Returns:
        {
          "total_judged": int,
          "position_bias_rate": float,        # 0-1, cao = bias nhiều
          "position_bias_count": int,
          "verbosity_bias": float,            # 0-1, > 0.6 = đáng lo ngại
          "verbosity_details": {
            "a_wins_a_longer": int,           # A thắng VÀ A dài hơn
            "b_wins_b_longer": int,           # B thắng VÀ B dài hơn
            "total_decisive": int,            # tổng case có winner rõ ràng
          },
          "interpretation": str,
        }
    """
    # HƯỚNG DẪN GỐC (đã implement bên dưới): Task 8 - Bias report
    # total = len(judge_results)
    # if total == 0:
    #     return {"total_judged": 0, "position_bias_rate": 0.0, "verbosity_bias": 0.0}
    #
    # position_bias_count = sum(1 for r in judge_results if not r.position_consistent)
    # position_bias_rate  = position_bias_count / total
    #
    # a_wins_a_longer = sum(
    #     1 for r in judge_results
    #     if r.final_winner == "A" and len(r.answer_a) > len(r.answer_b)
    # )
    # b_wins_b_longer = sum(
    #     1 for r in judge_results
    #     if r.final_winner == "B" and len(r.answer_b) > len(r.answer_a)
    # )
    # decisive = sum(1 for r in judge_results if r.final_winner != "tie")
    # verbosity_bias = (a_wins_a_longer + b_wins_b_longer) / decisive if decisive > 0 else 0.0
    #
    # interpretation = ("Position bias cao — nên dùng swap-and-average."
    #                   if position_bias_rate > 0.3 else "Position bias thấp — judge ổn định.")
    # return {
    #     "total_judged": total, "position_bias_rate": round(position_bias_rate, 3),
    #     "position_bias_count": position_bias_count,
    #     "verbosity_bias": round(verbosity_bias, 3),
    #     "verbosity_details": {"a_wins_a_longer": a_wins_a_longer,
    #                           "b_wins_b_longer": b_wins_b_longer,
    #                           "total_decisive": decisive},
    #     "interpretation": interpretation,
    # }
    total = len(judge_results)
    if total == 0:
        return {"total_judged": 0, "position_bias_rate": 0.0, "position_bias_count": 0,
                "verbosity_bias": 0.0, "verbosity_details": {}, "interpretation": ""}

    position_bias_count = sum(1 for r in judge_results if not r.position_consistent)
    position_bias_rate  = position_bias_count / total

    a_wins_a_longer = sum(
        1 for r in judge_results
        if r.final_winner == "A" and len(r.answer_a) > len(r.answer_b)
    )
    b_wins_b_longer = sum(
        1 for r in judge_results
        if r.final_winner == "B" and len(r.answer_b) > len(r.answer_a)
    )
    decisive = sum(1 for r in judge_results if r.final_winner != "tie")
    verbosity_bias = (a_wins_a_longer + b_wins_b_longer) / decisive if decisive > 0 else 0.0

    interpretation = ("Position bias cao — nên dùng swap-and-average."
                       if position_bias_rate > 0.3 else "Position bias thấp — judge ổn định.")
    return {
        "total_judged": total, "position_bias_rate": round(position_bias_rate, 3),
        "position_bias_count": position_bias_count,
        "verbosity_bias": round(verbosity_bias, 3),
        "verbosity_details": {"a_wins_a_longer": a_wins_a_longer,
                              "b_wins_b_longer": b_wins_b_longer,
                              "total_decisive": decisive},
        "interpretation": interpretation,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def _judge_correctness(question: str, model_answer: str, ground_truth: str) -> tuple[int, str]:
    """Judge nhị phân đúng/sai — DÙNG RIÊNG cho Cohen's κ (Task 7), khác với pairwise_judge.

    Lý do cần một judge riêng: pairwise_judge() (Task 5) trả lời câu hỏi "answer nào TỐT HƠN",
    và ground_truth luôn đầy đủ/chi tiết hơn model_answer nên gần như luôn "thắng" — kể cả khi
    model_answer đã đúng về mặt thông tin. Dùng winner đó làm nhãn đúng/sai sẽ luôn ra 0
    (không khớp ý nghĩa human_label = đúng/sai thông tin), khiến κ vô nghĩa.
    Ở đây hỏi thẳng: model_answer có ĐÚNG so với ground_truth không (bỏ qua việc thiếu chi tiết
    phụ, chỉ tính sai khi có thông tin sai lệch/mâu thuẫn với ground_truth).
    """
    from openai import OpenAI
    client = OpenAI()
    prompt = f'''Câu hỏi: {question}

Đáp án tham chiếu (ground truth): {ground_truth}

Câu trả lời cần đánh giá: {model_answer}

Câu trả lời trên có ĐÚNG về mặt thông tin so với đáp án tham chiếu không?
Chỉ coi là "incorrect" nếu có thông tin sai lệch hoặc mâu thuẫn với đáp án tham chiếu.
Thiếu chi tiết phụ (không làm sai bản chất câu trả lời) vẫn tính là "correct".
Trả lời JSON (chỉ JSON): {{"correct": true hoặc false, "reasoning": "giải thích ngắn gọn"}}
'''
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": "Bạn là expert đánh giá độ chính xác câu trả lời RAG. Chỉ trả lời JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    return (1 if data.get("correct") else 0), data.get("reasoning", "")


def _load_bottom5_question_ids() -> list[int]:
    """Lấy 5 câu hỏi RAGAS chấm tệ nhất (Phase A) để soi judge trên case khó."""
    path = os.path.join(_ROOT_DIR, "reports", "ragas_50q.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            report = json.load(f)
        ids = [item["question_id"] for item in report.get("bottom_10", [])[:5]]
        if ids:
            return ids
    return [1, 2, 3, 4, 5]


def run_phase_b(path: str = "reports/judge_results.json") -> dict:
    """Chạy toàn bộ Phase B: swap-and-average trên 5 case khó nhất (bias report)
    + pairwise judge (model_answer vs ground_truth) trên 10 câu có human label
    (cohen's κ), rồi lưu report."""
    with open(ANSWERS_PATH, encoding="utf-8") as f:
        answers = {a["id"]: a for a in json.load(f)}
    with open(TEST_SET_PATH, encoding="utf-8") as f:
        test_set = {q["id"]: q for q in json.load(f)}
    with open(HUMAN_LABELS_PATH, encoding="utf-8") as f:
        human_data = json.load(f)

    # 1) Swap-and-average trên 5 câu bottom RAGAS → bias_report
    bottom5_ids = _load_bottom5_question_ids()
    swap_results: list[JudgeResult] = []
    pairwise_samples = []
    for qid in bottom5_ids:
        if qid not in answers or qid not in test_set:
            continue
        question = answers[qid]["question"]
        model_answer = answers[qid]["answer"]
        ground_truth = test_set[qid]["ground_truth"]
        print(f"[swap-and-average] q{qid}: {question[:60]}...")
        r = swap_and_average(question, model_answer, ground_truth)
        swap_results.append(r)
        pairwise_samples.append({
            "question_id": qid, "question": question,
            "winner_pass1": r.winner_pass1, "winner_pass2": r.winner_pass2,
            "final_winner": r.final_winner,
            "position_consistent": r.position_consistent,
            "reasoning_pass1": r.reasoning_pass1, "reasoning_pass2": r.reasoning_pass2,
        })

    bias = bias_report(swap_results)
    print(f"\nBias report: {bias}")

    # 2) Correctness judge (model_answer vs ground_truth) trên 10 câu human-labeled → Cohen's κ
    judge_details = []
    human_labels, judge_labels = [], []
    for item in human_data:
        qid = item["question_id"]
        gt = test_set.get(qid, {}).get("ground_truth", "")
        print(f"[correctness] q{qid}: {item['question'][:60]}...")
        judge_label, reasoning = _judge_correctness(item["question"], item["model_answer"], gt)
        human_labels.append(item["human_label"])
        judge_labels.append(judge_label)
        judge_details.append({
            "question_id": qid, "question": item["question"],
            "human_label": item["human_label"], "judge_label": judge_label,
            "agree": judge_label == item["human_label"],
            "judge_reasoning": reasoning,
        })

    kappa = cohen_kappa(judge_labels, human_labels)
    if kappa > 0.8:
        interp = "almost perfect"
    elif kappa > 0.6:
        interp = "substantial"
    elif kappa > 0.4:
        interp = "moderate"
    elif kappa > 0.2:
        interp = "fair"
    elif kappa > 0.0:
        interp = "slight"
    else:
        interp = "poor"
    print(f"\nCohen's κ: {kappa:.3f} ({interp})")

    report = {
        "pairwise_samples": pairwise_samples,
        "bias_report": bias,
        "judge_vs_human": {
            "cohen_kappa": round(kappa, 4),
            "interpretation": interp,
            "details": judge_details,
        },
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nPhase B report saved → {path}")
    return report


if __name__ == "__main__":
    run_phase_b()
