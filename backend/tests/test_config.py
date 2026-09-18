"""Unit tests for configuration loading and validation."""

import os

import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def clean_settings_environment(monkeypatch):
    fields = {name.upper() for name in Settings.model_fields}
    for name in os.environ:
        if name.upper().split("__", 1)[0] in fields:
            monkeypatch.delenv(name)


def test_local_accepts_defaults():
    config = Settings()

    assert config.ENV == "local"
    assert config.EMBEDDING_DIM == 384
    assert config.GIT_SHA == "dev"
    assert config.KNOWLEDGE.h0 == 24


def test_local_accepts_environment_values(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("EMBEDDING_DIM", "128")
    monkeypatch.setenv("LLM_FORCE_DOWN", "1")
    monkeypatch.setenv("KNOWLEDGE__OBSERVER_EVERY_N", "12")

    config = Settings()

    assert config.JWT_SECRET.get_secret_value() == "test-secret"
    assert config.EMBEDDING_DIM == 128
    assert config.LLM_FORCE_DOWN is True
    assert config.KNOWLEDGE.observer_every_n == 12
    assert config.KNOWLEDGE.h0 == 24


@pytest.mark.parametrize("secret", ["", "x" * 31, "я" * 15])
def test_prod_rejects_short_jwt_secret(secret):
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(ENV="prod", JWT_SECRET=secret)


@pytest.mark.parametrize("secret", ["x" * 32, "я" * 16])
def test_prod_accepts_32_byte_jwt_secret(secret):
    assert Settings(ENV="prod", JWT_SECRET=secret).ENV == "prod"


@pytest.mark.parametrize("dimension", [0, -1])
def test_rejects_nonpositive_embedding_dim(dimension):
    with pytest.raises(ValidationError, match="EMBEDDING_DIM"):
        Settings(EMBEDDING_DIM=dimension)


def test_rejects_unknown_environment():
    with pytest.raises(ValidationError, match="ENV"):
        Settings(ENV="staging")


def test_secret_not_exposed_in_repr_or_validation_message():
    secret = "test-private-value"
    assert secret not in repr(Settings(JWT_SECRET=secret))
    with pytest.raises(ValidationError) as error:
        Settings(ENV="prod", JWT_SECRET=secret)
    assert secret not in str(error.value)
