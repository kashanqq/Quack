"""Optional layer loading shared by the API and the workers.

B1 (`app.graph.*`), B2 (`app.llm.*`, `app.agents.*`) и платформа B3 живут в
разных ветках: приложение обязано подниматься, даже если соседнего слоя в
этой копии ещё нет. Функция отличает «модуля нет» от «модуль есть, но
падает при импорте» — второе всегда ошибка и пробрасывается.
"""

from importlib import import_module
from typing import Any


def optional_layer(name: str) -> Any | None:
    """Import `name`, or return None when that module itself is missing."""
    try:
        return import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name and (name == exc.name or name.startswith(f"{exc.name}.")):
            return None
        raise
