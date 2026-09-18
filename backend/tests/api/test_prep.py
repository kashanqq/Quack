"""Knowledge version endpoint contract."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import deps
from app.api.auth import issue_token
from app.keys import knowledge_version
from app.main import create_app


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.keys: list[str] = []

    async def get(self, key: str) -> str | None:
        self.keys.append(key)
        return self.values.get(key)


def test_knowledge_version_is_authenticated_and_student_scoped():
    app = create_app()
    redis = FakeRedis()
    app.dependency_overrides[deps.get_redis] = lambda: redis
    first, second = uuid4(), uuid4()
    redis.values[knowledge_version(str(first))] = "7"

    with TestClient(app) as client:
        assert client.get("/prep/knowledge/version").status_code == 401
        client.cookies.set("quack_token", issue_token(first, "first@quack.kz"))
        first_response = client.get("/prep/knowledge/version")
        client.cookies.set("quack_token", issue_token(second, "second@quack.kz"))
        second_response = client.get("/prep/knowledge/version")

    assert first_response.status_code == 200
    assert first_response.json() == {"version": 7}
    assert second_response.status_code == 200
    assert second_response.json() == {"version": 0}
    assert redis.keys == [knowledge_version(str(first)), knowledge_version(str(second))]
