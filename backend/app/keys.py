"""Frozen Redis key contract; pure key construction without Redis access."""


def session(student_id: str) -> str:
    return f"quack:session:{student_id}"


def llm_status() -> str:
    return "quack:llm:status"


def llm_ratelimit(slot: str) -> str:
    return f"quack:llm:ratelimit:{slot}"


def llm_errors() -> str:
    return "quack:llm:errors"


def llm_probe() -> str:
    return "quack:llm:probe"


def login_ratelimit(ip: str) -> str:
    return f"quack:auth:rl:{ip}"


def knowledge_version(student_id: str) -> str:
    return f"quack:knowledge:version:{student_id}"


def forecast(student_id: str, exam_id: str) -> str:
    return f"quack:forecast:{student_id}:{exam_id}"


def ctx_topic(student_id: str, skill_id: str) -> str:
    return f"quack:ctx:topic:{student_id}:{skill_id}"


def lock(name: str) -> str:
    return f"quack:lock:{name}"


def matching_snapshot(student_id: str) -> str:
    """Last matching the selection assistant showed (docs/tz/phase3 §3.3)."""
    return f"quack:matching:snapshot:{student_id}"


# --- phase 4 (docs/tz/40-phase4-background-quack.md §1.8) ---


def text_job(kind: str, input_hash: str) -> str:
    """Id задачи, которая сейчас генерирует этот текст; TTL 600 с."""
    return f"quack:text:job:{kind}:{input_hash}"


def search_ratelimit() -> str:
    return "quack:search:rl"


def search_monthly(yyyymm: str) -> str:
    return f"quack:search:month:{yyyymm}"


def search_last_error() -> str:
    return "quack:search:last_error"


def search_status(search_id: str) -> str:
    return f"quack:search:status:{search_id}"


def cron_last(name: str) -> str:
    return f"quack:cron:last:{name}"


def quack_batch(student_id: str) -> str:
    return f"quack:recs:batch:{student_id}"


def soft_pending(student_id: str) -> str:
    return f"quack:softmatch:pending:{student_id}"


def pace(student_id: str) -> str:
    return f"quack:pace:{student_id}"
