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
