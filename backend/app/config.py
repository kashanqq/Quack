"""Application settings loaded from environment variables."""

from typing import Literal, Self

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class KnowledgeParams(BaseModel):
    """Parameter names, units and defaults from memory-architecture-quack.md §12."""

    alpha: float = 1.0
    beta: float = 0.5
    h0: float = 24
    h0_prior: float = 240
    h_min: float = 12
    h_max: float = 8760
    k_confidence: float = 3.0
    p_chat_cap: float = 0.8
    p_target_max: float = 0.95
    c_vis: float = 0.3
    c_close: float = 0.6
    c_cov: float = 0.6
    transfer_cross_exam: float = 0.6
    seen_template_factor: float = 0.8
    unmatched_incorrect_factor: float = 0.7
    prior_indirect_weight: float = 0.3
    misc_confirm_min_occ: int = 2
    misc_resolve_avoided: int = 3
    under_watch_days: int = 14
    trigger_min_n: int = 3
    trigger_min_share: float = 0.75
    root_window_days: int = 30
    root_boost: float = 1.5
    canon_merge: float = 0.90
    canon_adjudicate: float = 0.80
    min_templates_personal: int = 3
    observer_every_n: int = 6
    observer_min_confidence: float = 0.7
    diag_base: int = 8
    diag_reserve: int = 4
    diag_max: int = 12
    set_size: int = 3
    chat_window: int = 10
    context_budget_tokens: int = 3000

    check_size: int = 3
    review_window_days: int = 7
    consolidation_days: int = 7
    mock_set_min: int = 8
    mock_set_max: int = 12
    mock_topic_min: int = 5
    mock_topic_max: int = 7
    mock_misc_n: int = 3
    diag_reask_after: int = 3
    min_candidates: int = 3
    matching_priority_weights: dict[str, int] = Field(
        default_factory=lambda: {
            "realism": 3,
            "cost": 2,
            "ranking": 1,
            "location": 1,
            "program": 2,
            "research": 1,
            "mobility": 1,
        }
    )


class Settings(BaseSettings):
    """Infrastructure and application configuration, without service initialization."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
        hide_input_in_errors=True,
    )

    ENV: Literal["local", "prod"] = "local"
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://quack:quack-local-postgres@127.0.0.1:5432/quack",
        repr=False,
    )
    NEO4J_URI: str = "bolt://127.0.0.1:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = SecretStr("quack-local-neo4j")
    REDIS_URL: str = Field(default="redis://127.0.0.1:6379/0", repr=False)

    JWT_SECRET: SecretStr = SecretStr("quack-local-only-development-secret")
    JWT_TTL_DAYS: int = 30

    LLM_BASE_URL: str = ""
    LLM_API_KEY: SecretStr = SecretStr("")
    MODEL_CHAT: str = ""
    MODEL_BULK: str = ""
    LLM_STRUCTURED_MODE: Literal["response_format", "tool"] = "response_format"
    LLM_STRICT_SCHEMA: bool = False
    LLM_REASONING_CHAT: str | None = "low"
    LLM_REASONING_BULK: str | None = "high"
    LLM_TIMEOUT_CHAT_S: float = 30
    LLM_TIMEOUT_BULK_S: float = 90
    # Local starting limits; configure these for the selected provider.
    LLM_RPM_CHAT: int = 10
    LLM_RPM_BULK: int = 10
    LLM_FORCE_DOWN: bool = False

    @field_validator("LLM_REASONING_CHAT", "LLM_REASONING_BULK", mode="before")
    @classmethod
    def _empty_reasoning_means_unset(cls, value: object) -> object:
        """An empty env value means "don't pass reasoning_effort at all",
        not the literal string "" (docs/decisions/llm-provider.md, TTFT
        matrix) — ``LLMClient`` already treats ``None`` this way."""
        if value == "":
            return None
        return value

    TAVILY_API_KEY: SecretStr = SecretStr("")
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    EMBEDDING_DIM: int = Field(default=384, gt=0)
    LOG_LEVEL: str = "INFO"
    GIT_SHA: str = "dev"
    KNOWLEDGE: KnowledgeParams = Field(default_factory=KnowledgeParams)

    @property
    def knowledge(self) -> KnowledgeParams:
        """Phase 2 access to the existing Phase 1 knowledge settings."""
        return self.KNOWLEDGE

    @model_validator(mode="after")
    def validate_prod_jwt_secret(self) -> Self:
        if self.ENV == "prod":
            secret_bytes = self.JWT_SECRET.get_secret_value().encode("utf-8")
            if len(secret_bytes) < 32:
                raise ValueError("JWT_SECRET must be at least 32 bytes in prod")
        return self


settings = Settings()
