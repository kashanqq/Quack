# Graph Report - backend  (2026-09-18)

## Corpus Check
- 169 files · ~70,076 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .ini 1, .cypher 1)

## Summary
- 1553 nodes · 3775 edges · 113 communities (75 shown, 38 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 334 edges (avg confidence: 0.93)
- Token cost: 137,244 input · 0 output

## Community Hubs (Navigation)
- Knowledge Half-Life Model
- Database Models
- Auth & User Seeding
- Graph Queries & Set Assembly
- Alembic Migrations & DB Tests
- Profile API & DB Schemas
- Web Search & Workers
- Logging & API Root
- Personal Graph Queries
- Event Dispatch
- Knowledge Base Graph Queries
- Exam Formats & Graph Labels
- Auth Dependencies
- Task Answer Schemas
- Task Answer Evaluation
- Session Keys & Events
- Agent Prompt Docs
- Selection Agent Tools
- Auth API Tests
- Task Answer Grading
- Chat Agent Router
- Knowledge Weights
- LLM Client Core
- LLM Client Protocol
- Event Types & Store Tests
- Postcheck Fact Verification
- Task Rendering
- Config Settings Tests
- LLM Probe Script
- LLM Fake & Structured Output
- Seed Data Schema Tests
- API Dependencies
- Chat API
- Saved Programs Repo
- Skills Seeding
- Canonical Graph Query Tests
- LLM Loop
- Chat SSE Tests
- Auth API Endpoints
- Health API
- Embeddings & Seeding
- Worker Entrypoint
- Hard Match Filtering
- Agent Job Orchestration
- Chat App Wiring
- Program Cache Repo
- App Error Types
- Event Dispatch Tests
- SSOT Memory Architecture Copy
- Error Contract Tests
- Common Schemas
- SSOT Arch Logic Copy
- Set Templates Seeding
- Rate-Limited Login Tests
- Observer Agent
- SSE Streaming
- Task Generation
- Session Dependency Tests
- Graph Context Builder
- SSOT Arch Layers Copy
- Task Generators
- Prep API Tests
- SSOT Memory Concepts Copy
- SSOT Product Logic Evidence
- Tutor Agent Tools
- Matching Comparison
- Program Schemas
- Knowledge Reconciliation
- API Test Fixtures
- LLM Client Status
- SSOT Product Logic Recommendations
- Alembic Initial Migration
- SSOT Memory Events Log
- SSOT Skill Layers
- SSOT Task Dataset Concepts
- SSOT Program Requirements
- Agents Package Init
- API Package Init
- DB Package Init
- DB Repo Package Init
- Events Package Init
- App Package Init
- LLM Package Init
- Schemas Package Init
- Search Package Init
- Seed Package Init
- Workers Package Init
- API Tests Package Init
- DB Tests Package Init
- Events Tests Package Init
- Tests Package Init
- Seed Tests Package Init
- SSOT Exam Calendars
- SSOT Program Cache Concept
- SSOT Task Dataset Concept
- SSOT Events Source of Truth
- SSOT Tutor vs Observer
- SSOT Program Comparison
- SSOT Exam Format Concept
- SSOT Matching Assistant Chat
- SSOT Overview Tab Concept
- SSOT Program Concept
- SSOT Program Search Cache
- Quack API Package

## God Nodes (most connected - your core abstractions)
1. `Settings` - 39 edges
2. `LLMClient` - 32 edges
3. `create_app()` - 30 edges
4. `KnowledgeParams` - 29 edges
5. `LLMMessage` - 29 edges
6. `EventType` - 27 edges
7. `Program` - 27 edges
8. `get_current_student()` - 25 edges
9. `TaskTemplateSpec` - 25 edges
10. `LLMUnavailable` - 24 edges

## Surprising Connections (you probably didn't know these)
- `test_metadata_has_all_phase1_tables_and_constraints()` --uses--> `Base`  [INFERRED]
  tests/db/test_migrations.py → app/db/models.py
- `Quack Backend README` --references--> `Phase 1 Shared Contracts`  [AMBIGUOUS]
  README.md → docs/tz/00-contracts.md
- `run_structured_probe()` --uses--> `ObservationOut`  [INFERRED]
  scripts/llm_probe.py → app/agents/observer.py
- `_postgres()` --calls--> `text()`  [INFERRED]
  app/api/health.py → tests/test_workers_search.py
- `print_echo_probe()` --uses--> `Settings`  [INFERRED]
  scripts/llm_probe.py → app/config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Шесть слоёв архитектуры Quack (L1–L6)** — backend_ssot_arch_logic_l1_client, backend_ssot_arch_logic_l2_orchestration, backend_ssot_arch_logic_l3_ai_layer, backend_ssot_arch_logic_l4_deterministic_rules, backend_ssot_arch_logic_l5_data_storage, backend_ssot_arch_logic_l6_external_sources [EXTRACTED 1.00]
- **Инструменты, доступные языковой модели (L2)** — backend_ssot_arch_logic_get_exam_format, backend_ssot_arch_logic_get_admission_route, backend_ssot_arch_logic_get_program_requirements, backend_ssot_arch_logic_save_profile_field, backend_ssot_arch_logic_run_program_search, backend_ssot_arch_logic_save_program, backend_ssot_arch_logic_get_skill_state [EXTRACTED 1.00]
- **Конвейер доверия к свидетельствам (ярусы → Evidence → KnowledgeState через HLR)** — backend_ssot_memory_architecture_quack_trust_tiers, backend_ssot_memory_architecture_quack_evidence, backend_ssot_memory_architecture_quack_knowledgestate, backend_ssot_memory_architecture_quack_half_life_regression [INFERRED 0.85]
- **Phase 1 Agent Prompt Files (v1)** — app_agents_prompts_selection_v1, app_agents_prompts_tutor_v1, app_agents_prompts_observer_v1, app_agents_prompts_extract_program_v1 [EXTRACTED 1.00]
- **LLM Provider Decision Documentation Chain** — ssot_tech_stack, docs_tz_30_b2, docs_decisions_llm_provider, docs_tz_checklists_phase1_b2 [EXTRACTED 1.00]
- **B2 Sync-Log Contract Deviations** — docs_sync_log, concept_tool_read_only_param, concept_get_program_facts_naming, concept_loopend_naming_resolution, concept_observation_confidence_revision [EXTRACTED 1.00]

## Communities (113 total, 38 thin omitted)

### Community 0 - "Knowledge Half-Life Model"
Cohesion: 0.06
Nodes (67): KnowledgeParams, BaseModel, Application settings loaded from environment variables., Parameter names, units and defaults from memory-architecture-quack.md §12., close_driver(), create_driver(), AsyncDriver, Neo4j driver lifecycle — soft-fail wrapper. B3 connects this from… (+59 more)

### Community 1 - "Database Models"
Cohesion: 0.07
Nodes (44): Base, DailyAggregate, GeneratedText, Message, PostgreSQL Phase 1 persistence schema., Recommendation, SeenTemplate, SetSummary (+36 more)

### Community 2 - "Auth & User Seeding"
Cohesion: 0.06
Nodes (41): hash_password(), verify_password(), User, get_user(), get_user_by_email(), AsyncSession, UUID, User persistence; transaction ownership remains with the caller. (+33 more)

### Community 3 - "Graph Queries & Set Assembly"
Cohesion: 0.07
Nodes (45): get_dependents(), get_exam_format(), get_skill(), list_areas(), list_misconceptions_for_skill(), list_templates_for_skill(), _load_map(), Any (+37 more)

### Community 4 - "Alembic Migrations & DB Tests"
Cohesion: 0.09
Nodes (34): Alembic environment using the application async PostgreSQL settings., run_migrations_in_transaction(), run_migrations_online(), app_db, close_engine(), create_engine(), create_sessionmaker(), AsyncSession (+26 more)

### Community 5 - "Profile API & DB Schemas"
Cohesion: 0.11
Nodes (32): AsyncSession, Depends, Redis, update_profile(), Profile, apply_profile_update(), get_profile(), profile_readiness() (+24 more)

### Community 6 - "Web Search & Workers"
Cohesion: 0.08
Nodes (26): SearchHit, app_search, _ddgs(), fetch_page(), Program search and bounded page text retrieval., search_programs(), _tavily(), extract_program() (+18 more)

### Community 7 - "Logging & API Root"
Cohesion: 0.07
Nodes (23): app_api, configure_logging(), mask_secrets(), _mask_value(), Any, Redact secret-bearing fields, including nested structured fields., create_app(), request_id_middleware() (+15 more)

### Community 8 - "Personal Graph Queries"
Cohesion: 0.13
Nodes (34): add_root_cause(), ensure_student(), get_misc_states(), get_state(), get_states(), list_evidence(), merge_evidence(), AsyncDriver (+26 more)

### Community 9 - "Event Dispatch"
Cohesion: 0.13
Nodes (30): Event, dispatch(), AsyncSession, Synchronous-in-transaction event handler registry., append(), list_events(), list_unprocessed(), mark_processed() (+22 more)

### Community 10 - "Knowledge Base Graph Queries"
Cohesion: 0.08
Nodes (30): app_graph, get_admission_route(), list_facts_about(), list_requirements(), list_test_dates(), AsyncDriver, Read-only queries over the admission knowledge base (Neo4j). Source: memory-…, All routes for a country, each with requirements. (+22 more)

### Community 11 - "Exam Formats & Graph Labels"
Cohesion: 0.11
Nodes (29): String constants for all Neo4j labels and relationship types. Source: memory-…, _as_json(), ExamFormatFile, AsyncDriver, BaseModel, Path, Load exam formats (sections, scale table) into Neo4j — memory-architecture…, Load every .json under data/exam_formats/. (+21 more)

### Community 12 - "Auth Dependencies"
Cohesion: 0.15
Nodes (28): me(), get_current_student(), get_session(), AsyncSession, Commit a successful request and roll back a failed one., get_profile(), get_program(), list_programs() (+20 more)

### Community 13 - "Task Answer Schemas"
Cohesion: 0.15
Nodes (27): AnswerIn, AnswerResult, DistractorSpec, OmissionTrap, ParamSpec, BaseModel, Task persistence contracts from the shared Phase 1 specification., TaskTemplateSpec (+19 more)

### Community 14 - "Task Answer Evaluation"
Cohesion: 0.13
Nodes (27): check_constraints(), equal_values(), eval_expr(), Exception, Safe evaluation of template expressions — memory-architecture-quack.md §3.1. No…, Canonical string for comparing answers: nsimplify → str(simplify(...))., True iff a and b are mathematically equal., Raised when a template expression is invalid, unsafe, or yields no value. (+19 more)

### Community 15 - "Session Keys & Events"
Cohesion: 0.10
Nodes (13): app, current_session_id(), Redis, UUID, Redis-backed 30-minute student activity sessions., Frozen Redis key contract; pure key construction without Redis access., session(), FakeRedis (+5 more)

### Community 16 - "Agent Prompt Docs"
Cohesion: 0.15
Nodes (27): Extract Program Prompt v1, Observer Prompt v1, Selection Assistant Prompt v1, Selection Assistant Prompt v2, Tutor Prompt v1, LLM Circuit Breaker, backend/docs Ignored by .gitignore Issue, get_program_facts Naming Decision (+19 more)

### Community 17 - "Selection Agent Tools"
Cohesion: 0.20
Nodes (24): AdmissionRouteArgs, compare(), CompareArgs, ExamFormatArgs, get_admission_route(), get_exam_format(), get_program_facts(), ProgramFactsArgs (+16 more)

### Community 18 - "Auth API Tests"
Cohesion: 0.10
Nodes (18): issue_token(), UUID, app_events, test_me_invokes_b1_interface_when_available(), test_me_still_answers_when_graph_is_unavailable(), test_student_identity_only_comes_from_token(), profile_app(), ProfileSession (+10 more)

### Community 19 - "Task Answer Grading"
Cohesion: 0.20
Nodes (24): Grade, TaskInstance, grade(), _grade_mcq(), _grade_multi_select(), _grade_numeric(), _num_equal(), Any (+16 more)

### Community 20 - "Chat Agent Router"
Cohesion: 0.17
Nodes (22): AgentDeps, ChatKind, StreamEvent, Chat entrypoint — dispatches an incoming message to the right agent. Phase 1…, Dependencies handed to every agent and, through it, every tool call.…, Stream a reply to one chat message. Phase 1 is echo-only: exactly two messages…, run_chat(), StreamEvent (+14 more)

### Community 21 - "Knowledge Weights"
Cohesion: 0.14
Nodes (23): base_weight(), evidence_weight(), is_strong(), Tiers and weights for evidence — memory-architecture-quack.md §4.3, §8.1. Pure…, Tier 1 — mock/diagnostic; tier 2 — task, chat with a real solution; tier 3 —…, Base weight from the §4.3 table. Falls back to 0.0 for unknown combos., base * seen_template_factor (if repeated) * unmatched factor., Tiers 1 and 2 count as strong evidence; tier 3 does not. (+15 more)

### Community 22 - "LLM Client Core"
Cohesion: 0.21
Nodes (7): LLMClient, BaseModel, Exception, ModelSlot, Redis, LLMUsage, Timeout

### Community 23 - "LLM Client Protocol"
Cohesion: 0.15
Nodes (15): LLMLike, StreamEvent, T, FakeCall, FakeLLMClient, LLMStatus, ModelSlot, StreamEvent (+7 more)

### Community 24 - "Event Types & Store Tests"
Cohesion: 0.17
Nodes (16): EventType, StrEnum, empty_registry(), _event_in(), FakeRedis, FakeSession, fixture, Event-store ordering, validation, and SQL contracts without live services. (+8 more)

### Community 25 - "Postcheck Fact Verification"
Cohesion: 0.13
Nodes (18): check_facts(), _collect_result_values(), _extract_dates(), _extract_numbers(), _format_date(), _format_number(), _month_from_match(), _overlaps() (+10 more)

### Community 26 - "Task Rendering"
Cohesion: 0.15
Nodes (21): _format_raw(), Any, Render template strings — memory-architecture-quack.md §3.1. - render_stem:…, Substitute {name} placeholders. Rule for parentheses: if a substituted value is…, Format a sympy value. - integer: Integer only - fraction: 'a/b' for Rational,…, Render a raw param for embedding into a stem string., Rational → decimal string without trailing zeros., render_stem() (+13 more)

### Community 27 - "Config Settings Tests"
Cohesion: 0.14
Nodes (18): model_validator, Infrastructure and application configuration, without service initialization., An empty env value means "don't pass reasoning_effort at all", not the literal…, Settings, BaseSettings, field_validator, Self, clean_settings_environment() (+10 more)

### Community 28 - "LLM Probe Script"
Cohesion: 0.18
Nodes (19): LLMUnavailable, load_prompt(), ToolCallOut, argparse, Namespace, EchoProbeRun, _main(), _observer_messages() (+11 more)

### Community 29 - "LLM Fake & Structured Output"
Cohesion: 0.17
Nodes (15): Deterministic LLMLike implementation for tests — no network, no Redis. Each…, parse_structured_output(), T, Shared structured-output parsing/retry logic for LLMClient and FakeLLMClient.…, structured_validation_retry_message(), Structured JSON logging with request context and secret masking., HealthOut, BaseModel (+7 more)

### Community 30 - "Seed Data Schema Tests"
Cohesion: 0.23
Nodes (20): SkillsFile, _all_exam_format_files(), _all_skill_files(), _all_template_files(), _has_cycle(), dfs(), _load(), Path (+12 more)

### Community 31 - "API Dependencies"
Cohesion: 0.16
Nodes (17): client_ip(), get_graph(), get_llm(), get_redis(), Any, Redis, Request, FastAPI dependencies for infrastructure and authenticated students. (+9 more)

### Community 32 - "Chat API"
Cohesion: 0.14
Nodes (18): _agent_router(), _chat_id(), get_messages(), post_message(), Any, AsyncSession, ChatKind, Depends (+10 more)

### Community 33 - "Saved Programs Repo"
Cohesion: 0.20
Nodes (11): SavedProgram, list_saved(), UUID, remove_saved(), save_program(), Conflict, ProgramSession, asyncio (+3 more)

### Community 34 - "Skills Seeding"
Cohesion: 0.16
Nodes (18): AreaDef, AreaSkillRef, ensure_schema(), ExamHeader, AsyncDriver, BaseModel, Path, Load skill map and areas into Neo4j — memory-architecture-quack.md §2.1.… (+10 more)

### Community 35 - "Canonical Graph Query Tests"
Cohesion: 0.14
Nodes (16): get_prerequisites(), is_dag(), list_exam_skills(), Walk REQUIRES upward from skill_id up to `depth` hops., True if REQUIRES has no cycles. Used by tests and seed validation., All skills for an exam, with area_id and weight. Uses the exam's own area., fixture, Integration tests over the canonical layer — 20-B1.md §7. Require a live Neo4j… (+8 more)

### Community 36 - "LLM Loop"
Cohesion: 0.16
Nodes (12): build_tool_call(), LoopEnd, ModelSlot, StreamEvent, Tool-calling loop: model -> tool call -> result back to model. Drives…, run_tool_loop(), _safe_json(), Tool registry — plain Python functions with Pydantic arguments, no I/O.… (+4 more)

### Community 37 - "Chat SSE Tests"
Cohesion: 0.13
Nodes (12): TextDelta, _events(), _setup(), list_messages(), test_agent_error_is_last_without_assistant_write(), test_llm_unavailable_before_first_event_is_http_503(), test_missing_b2_returns_503_before_write(), test_oversized_text_rejected_before_stream() (+4 more)

### Community 38 - "Auth API Endpoints"
Cohesion: 0.16
Nodes (15): login(), logout(), AsyncSession, Depends, post, Redis, Request, Cookie-based student authentication. (+7 more)

### Community 39 - "Health API"
Cohesion: 0.21
Nodes (15): _bounded_check(), health(), HealthOut, _llm_status(), _neo4j(), _postgres(), BaseModel, Request (+7 more)

### Community 40 - "Embeddings & Seeding"
Cohesion: 0.14
Nodes (12): Embedder, Sentence embeddings — memory-architecture-quack.md §1.1, §5.4. Used only by…, Wrapper around sentence-transformers with lazy load and dimension check., Return L2-normalized embeddings, one per input text. Prefixes each text with…, MisconceptionFileEntry, AsyncDriver, BaseModel, Path (+4 more)

### Community 41 - "Worker Entrypoint"
Cohesion: 0.16
Nodes (16): _optional_layer(), Any, Load B1/B2 only when that layer is present in the checkout., app_workers, enqueue(), Any, ARQ queues and shared infrastructure lifecycle., shutdown() (+8 more)

### Community 42 - "Hard Match Filtering"
Cohesion: 0.18
Nodes (14): hard_filter(), HardResult, BaseModel, Hard factors — product-logic §3.3, memory-architecture §10.3. Phase 2 stub., Phase 2: score each program on requirements vs profile., BaseModel, rank(), Ranked (+6 more)

### Community 43 - "Agent Job Orchestration"
Cohesion: 0.18
Nodes (14): extract_program(), observe_chat(), pregenerate_set(), propose_personal_nodes(), UUID, ARQ job stubs (docs/tz/30-B2.md §5.5). Signatures only: an ARQ worker context…, Extract observations from a chat window and reconcile them into the knowledge…, Pre-generate guidelines and explanations for every topic in a set so they're… (+6 more)

### Community 44 - "Chat App Wiring"
Cohesion: 0.17
Nodes (10): Authenticated chat transport; agent behavior belongs to B2., FastAPI application factory and infrastructure lifecycle., fastapi_exceptions, importlib, inspect, starlette_middleware_base, starlette_responses, Chat transport tests with a fake implementation of the agreed B2 interface. (+2 more)

### Community 45 - "Program Cache Repo"
Cohesion: 0.30
Nodes (13): ProgramCache, get_program(), list_programs(), AsyncSession, Program cache and student-owned saved programs., _to_program(), upsert_program(), Program (+5 more)

### Community 46 - "App Error Types"
Cohesion: 0.27
Nodes (11): AppError, Forbidden, Exception, Frozen application error contract., SearchUnavailable, TooManyRequests, Unauthorized, UnsupportedMediaType (+3 more)

### Community 47 - "Event Dispatch Tests"
Cohesion: 0.18
Nodes (10): on(), Handler, pytest, empty_registry(), _event(), fixture, Handler registration order and failure propagation., test_handler_failure_stops_later_handlers() (+2 more)

### Community 48 - "SSOT Memory Architecture Copy"
Cohesion: 0.18
Nodes (14): Модель знаний ученика, Evidence (свидетельство), explain_belief(node_id), get_learner_context(...), Half-life regression (модель забывания), KnowledgeState, Контекст репетитора (<learner_model>, §9), Канонизация персональных заблуждений (§5.4) (+6 more)

### Community 49 - "Error Contract Tests"
Cohesion: 0.21
Nodes (8): NotFound, test_app_error_contract(), fail(), _program(), fixture, saved_app(), remove_saved(), save_program()

### Community 50 - "Common Schemas"
Cohesion: 0.21
Nodes (7): Page, BaseModel, Shared repository response types., _program(), programs_app(), fixture, Program read routes, filters, pagination, and authentication.

### Community 51 - "SSOT Arch Logic Copy"
Cohesion: 0.20
Nodes (12): Граф знаний о поступлении, get_admission_route, get_exam_format, get_program_requirements, get_skill_state, L1 Клиент, L2 Оркестрация / API, run_program_search (+4 more)

### Community 52 - "Set Templates Seeding"
Cohesion: 0.22
Nodes (10): _collect_trap_pairs(), AsyncDriver, AsyncSession, Path, Load task templates into Neo4j and Postgres cache — memory-architecture §3.1.…, Return [(distractor_key, misconception_id)] from all distractor sources., Validate all template files under path. Raises SeedError on first bad one.…, Walk data/templates/**/*.json and load each template. If session is given, also… (+2 more)

### Community 53 - "Rate-Limited Login Tests"
Cohesion: 0.18
Nodes (4): jwt, Authentication and dependency contracts without external services., test_ip_resolution_ignores_proxy_header_locally_and_uses_it_in_prod(), test_prod_cookie_is_secure()

### Community 54 - "Observer Agent"
Cohesion: 0.24
Nodes (8): Observation, ObservationOut, observe(), Any, BaseModel, model_validator, Observer — output schema for the prep-chat observer (docs/tz/30-B2.md §5.4).…, Run the observer over one window of chat messages (phase 2). Not implemented in…

### Community 55 - "SSE Streaming"
Cohesion: 0.24
Nodes (9): _frames(), StreamEvent, Server-sent events framing for the public chat stream., sse_response(), asyncio, collections_abc, contextlib, fastapi_responses (+1 more)

### Community 56 - "Task Generation"
Cohesion: 0.38
Nodes (9): Option, _build_mcq(), _build_multi_select(), _build_multi_select_traps(), _build_numeric(), Random, Instance generation from templates — memory-architecture-quack.md §3.1–3.4.…, Sample params; return first satisfying constraints. (+1 more)

### Community 57 - "Session Dependency Tests"
Cohesion: 0.20
Nodes (4): parametrize, test_session_dependency_commits_or_rolls_back(), check(), FakeSession

### Community 58 - "Graph Context Builder"
Cohesion: 0.28
Nodes (8): build_topic_context(), AsyncDriver, BaseModel, UUID, Context assembler for the tutor agent (phase 2). Source: memory-architecture-…, Slots for the tutor's context block (memory-architecture §9.2). Each slot is a…, Phase 2: assemble the tutor context from 4 parallel Cypher queries. See memory-…, TopicContext

### Community 59 - "SSOT Arch Layers Copy"
Cohesion: 0.33
Nodes (9): Деградация по слоям (§6.3): таймаут, предгенерация, статус «недоступно», L3 ИИ / языковая модель, L4 Детерминированные правила, L5 Данные и хранилище, L6 Внешние источники, Реактивность: «изменил → изменилось» (§02), Правило §7: модель не источник правды, пишет только через инструменты L4, Всё, что можно посчитать правилом, считается правилом (+1 more)

### Community 60 - "Task Generators"
Cohesion: 0.32
Nodes (6): _circle_chord(), generator(), Random, Registry of non-parametric task generators — memory-architecture-quack.md §3.5.…, Decorator to register a generator function under a name., Pick a Pythagorean triple (r, d, half); return chord length = 2*half. Distance…

### Community 61 - "Prep API Tests"
Cohesion: 0.38
Nodes (4): knowledge_version(), FakeRedis, Knowledge version endpoint contract., test_knowledge_version_is_authenticated_and_student_scoped()

### Community 62 - "SSOT Memory Concepts Copy"
Cohesion: 0.29
Nodes (7): Конфиг (§12, все параметры), Misconception (граф-узел, библиотечный+персональный), ROOT_CAUSE, Сборщик сетов (§10.1), Первичный замер (§4.2), Заблуждение (product-logic), Сеты (§4.3)

### Community 63 - "SSOT Product Logic Evidence"
Cohesion: 0.29
Nodes (7): Ничего без доказательства (memory-architecture), Свидетельство (product-logic), Подборка (§3.3), Ничего без доказательства, Профиль, Оценка реалистичности, Два источника правды (профиль + действия)

### Community 64 - "Tutor Agent Tools"
Cohesion: 0.40
Nodes (6): explain_belief(), ExplainBeliefArgs, get_task(), GetTaskArgs, Any, BaseModel

### Community 65 - "Matching Comparison"
Cohesion: 0.40
Nodes (5): compare(), Comparison, BaseModel, Comparison — product-logic §3.4. Phase 2 stub., Phase 2: side-by-side table across student-relevant and standard factors.

### Community 66 - "Program Schemas"
Cohesion: 0.47
Nodes (5): Deadline, BaseModel, Program contracts shared by repository consumers., Requirement, SavedProgram

### Community 67 - "Knowledge Reconciliation"
Cohesion: 0.40
Nodes (4): on_task_answered(), Event, Event → graph reconciliation (phase 2). Source: memory-architecture-quack.md…, Phase 2: apply task.answered (11 steps of §8.2). 1. Write event → event_id…

### Community 68 - "API Test Fixtures"
Cohesion: 0.40
Nodes (4): app_llm, fixture, API unit tests use B2's fake client during the real application lifespan., use_fake_llm()

### Community 69 - "LLM Client Status"
Cohesion: 0.40
Nodes (3): _decode(), Any, LLMStatus

### Community 70 - "SSOT Product Logic Recommendations"
Cohesion: 0.40
Nodes (5): Никакой лишней дисциплины, Рекомендации / Quack-лента (§3.6), Маршрут, Сет, Система рекомендует, ученик решает

### Community 72 - "SSOT Memory Events Log"
Cohesion: 0.50
Nodes (4): Лог событий (events, Postgres), Наблюдатель (чата подготовки), Replay (пересборка графа из событий), Чат подготовки (§4.5)

### Community 73 - "SSOT Skill Layers"
Cohesion: 0.67
Nodes (3): Каноническая карта навыков, Персональные узлы навыков, Карта навыков: канонический и персональный слои (§5.2)

### Community 74 - "SSOT Task Dataset Concepts"
Cohesion: 0.67
Nodes (3): Экземпляр задачи (TaskInstance, §3.3), Шаблон задачи (TaskTemplate, §3.1), Задачи и моки — датасет (§5.4)

### Community 75 - "SSOT Program Requirements"
Cohesion: 0.67
Nodes (3): Веха, Требование, Сохранённые (программы)

## Ambiguous Edges - Review These
- `Quack Backend README` → `Phase 1 Shared Contracts`  [AMBIGUOUS]
  README.md · relation: references
- `B1 Phase 1 Report (Engine and Graph)` → `Phase 1 Shared Contracts`  [AMBIGUOUS]
  docs/B1.md · relation: conceptually_related_to

## Knowledge Gaps
- **33 isolated node(s):** `WorkerInteractive`, `WorkerBulk`, `quack-api`, `L1 Клиент`, `Граф знаний о поступлении` (+28 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 571 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **38 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Quack Backend README` and `Phase 1 Shared Contracts`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `B1 Phase 1 Report (Engine and Graph)` and `Phase 1 Shared Contracts`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Settings` connect `Config Settings Tests` to `Knowledge Half-Life Model`, `Alembic Migrations & DB Tests`, `Event Dispatch`, `Rate-Limited Login Tests`, `LLM Client Core`, `LLM Probe Script`, `LLM Fake & Structured Output`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `KnowledgeParams` connect `Knowledge Half-Life Model` to `Graph Queries & Set Assembly`, `Knowledge Weights`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `LLMClient` connect `LLM Client Core` to `LLM Loop`, `Chat SSE Tests`, `LLM Client Status`, `LLM Client Protocol`, `Config Settings Tests`, `LLM Probe Script`, `LLM Fake & Structured Output`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `Settings` (e.g. with `create_engine()` and `create_driver()`) actually correct?**
  _`Settings` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `LLMClient` (e.g. with `Settings` and `LLMUnavailable`) actually correct?**
  _`LLMClient` has 11 INFERRED edges - model-reasoned connections that need verification._