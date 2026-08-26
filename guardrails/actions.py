"""Custom Colang actions for input-rail và output-rail keyword checks.

Auto-loaded by NeMo Guardrails from guardrails/actions.py.

GHI CHÚ: rails.co ban đầu dùng `user ask jailbreak` (một canonical-form match)
làm precondition ngay trong flow input rail. Theo nemoguardrails/rails/llm/llm_flows.co,
input rails chạy TRƯỚC khi hệ thống tạo UserIntent (`do run input rails` xảy ra trước
`do generate user intent` trong `process user input` / `run dialog rails`), nên một
statement `user X` bên trong input rail flow chờ một event không bao giờ được phát ra
— flow bị treo ở "Listen" và generate_async() trả về content rỗng, khiến check_input_rail()
luôn coi là allowed=True. Các rail chính thức của NeMo (activefence, autoalign...) đều
dùng `execute <action>(...)` để check rồi `if ... : bot ... / stop`, nên đổi sang pattern
đó bằng keyword-matching thuần Python thay vì canonical-form matching.

GHI CHÚ TƯƠNG TỰ cho output rail: flow gốc dùng `bot provide sensitive output`
(canonical-form match trên $bot_message). Khi gọi generate_async() ở chế độ
output-only (options.rails.dialog=False, dùng để test 1 câu trả lời cho sẵn —
xem check_output_rail() trong phase_c_guard.py), không có bước "generate bot
intent" thật sự chạy trước để phân loại $bot_message, nên canonical-form này
LUÔN khớp bất kể nội dung (đã verify bằng log.activated_rails: decision đầu
tiên luôn là 'provide sensitive output' dù bot_message hoàn toàn vô hại).
→ Cùng cách sửa: dùng execute check_sensitive_output(bot_message=$bot_message)
kiểm tra trực tiếp bằng Python thay vì để colang tự phân loại ngữ nghĩa.
"""

import re

from nemoguardrails.actions import action

JAILBREAK_KEYWORDS = [
    "bỏ qua tất cả",
    "pretend you are dan",
    "do anything now",
    "đóng vai",
    "ignore your system prompt",
    "unrestricted ai",
    "ai không có giới hạn",
    "forget your system prompt",
]

OFF_TOPIC_KEYWORDS = [
    "bài thơ",
    "nấu",
    "bitcoin",
    "ethereum",
    "giá cổ phiếu",
    "phim",
    "giải toán",
    "phương trình",
    "thời tiết",
    "tin tức",
]

PII_REQUEST_KEYWORDS = [
    "cho tôi biết cccd",
    "số điện thoại của nhân viên",
    "lương của nhân viên",
    "thông tin cá nhân của",
    "email của nhân viên",
    "tiết lộ thông tin nhân viên",
]

PROMPT_INJECTION_KEYWORDS = [
    "system override",
    "ignore previous instructions",
    "admin command",
    "system instructions",
]


SENSITIVE_OUTPUT_KEYWORDS = [
    "mật khẩu hệ thống",
    "cccd của nhân viên",
    "số điện thoại cá nhân của",
    "thông tin bí mật",
    "thông tin cá nhân của nhân viên",
]

_VN_CCCD_RE = re.compile(r"\b\d{9}(\d{3})?\b")
_VN_PHONE_RE = re.compile(r"\b0[3-9]\d{8}\b")


def _matches(user_message: str, keywords: list[str]) -> bool:
    text = user_message.lower()
    return any(kw in text for kw in keywords)


@action()
async def check_jailbreak(user_message: str) -> bool:
    return _matches(user_message, JAILBREAK_KEYWORDS)


@action()
async def check_off_topic(user_message: str) -> bool:
    return _matches(user_message, OFF_TOPIC_KEYWORDS)


@action()
async def check_pii_request(user_message: str) -> bool:
    return _matches(user_message, PII_REQUEST_KEYWORDS)


@action()
async def check_prompt_injection(user_message: str) -> bool:
    return _matches(user_message, PROMPT_INJECTION_KEYWORDS)


@action()
async def check_sensitive_output(bot_message: str) -> bool:
    if _matches(bot_message or "", SENSITIVE_OUTPUT_KEYWORDS):
        return True
    if _VN_PHONE_RE.search(bot_message or "") or _VN_CCCD_RE.search(bot_message or ""):
        return True
    return False
