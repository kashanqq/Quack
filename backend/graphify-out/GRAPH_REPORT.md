# Graph Report - backend  (2026-09-19)

## Corpus Check
- 285 files · ~140,442 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 3, .ini 1, .cypher 1)

## Summary
- 3252 nodes · 10210 edges · 184 communities (133 shown, 51 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1357 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d5a86ecf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- KnowledgeParams
- repo/tasks.py
- repo/users.py
- canonical.py
- test_store_integration.py
- errors.py
- config.py
- create_app
- 7. Применение — `app/apply/` (I/O)
- events.py
- kb.py
- knowledge_base.py
- StudentCtx
- TaskTemplateSpec
- test_evaluate.py
- keys.py
- Phase 1 Task Spec B2 (AI Layer)
- selection.py
- profile_app
- grade
- test_misconceptions.py
- test_weights.py
- LLMClient
- FakeLLMClient
- EventType
- postcheck.py
- test_render.py
- Settings
- LLMUnavailable
- llm/client.py
- test_data_schemas.py
- typing
- api/chat.py
- repo/programs.py
- skills.py
- exam_formats.py
- LLMMessage
- test_chat_sse.py
- dispatch.py
- api/health.py
- seed/misconceptions.py
- apply/knowledge.py
- test_rank.py
- jobs.py
- test_layers.py
- pathlib
- RuleDeps
- pytest
- Evidence (свидетельство)
- NotFound
- apply/diagnostic.py
- L2 Оркестрация / API
- seed_templates
- test_hard.py
- observer.py
- apply/mocks.py
- test_sets.py
- 3.4 Postgres — миграция `0002_phase2`
- build_topic_context
- L3 ИИ / языковая модель
- generators.py
- Profile
- ROOT_CAUSE
- Свидетельство (product-logic)
- apply/tasks.py
- test_compare.py
- schemas/knowledge.py
- reconcile.py
- api/conftest.py
- tasks/test_mocks.py
- Сет
- env.py
- Лог событий (events, Postgres)
- Карта навыков: канонический и персональный слои (§5.2)
- Экземпляр задачи (TaskInstance, §3.3)
- Сохранённые (программы)
- app/agents/__init__.py
- app/api/__init__.py
- app/db/__init__.py
- repo/__init__.py
- app/events/__init__.py
- app/__init__.py
- app/llm/__init__.py
- schemas/__init__.py
- search/__init__.py
- app/seed/__init__.py
- workers/__init__.py
- tests/api/__init__.py
- tests/db/__init__.py
- tests/events/__init__.py
- tests/__init__.py
- tests/seed/__init__.py
- Календари экзаменов
- Кэш программ
- Датасет задач (arch-logic)
- События — источник правды, граф — проекция
- Репетитор учит, наблюдатель запоминает
- Сравнение (§3.4)
- ExamFormat (product-logic §5.4)
- Чат подбора (§3.2)
- Обзор (§4.1)
- Программа
- Программы: веб-поиск + кэш (§5.1)
- quack-api
- repo/sets.py
- Program
- test_diagnostic_mocks_phase2.py
- test_sets_knowledge_phase2.py
- schemas/tasks.py
- knowledge/test_diagnostic.py
- reconcile_task_answer
- RootCauseOut
- test_assemble.py
- SkillWeight
- ExamFormat
- models.py
- tests/conftest.py
- test_task_answered.py
- apply_task_answered
- api/sets.py
- test_phase2.py
- api/matching.py
- test_profile_updated.py
- test_e2e_rules.py
- ТЗ фазы 2 — B1, правила и граф
- test_forecast.py
- test_gen_templates.py
- apply/test_diagnostic.py
- apply/sets.py
- Event
- api/mocks.py
- hlr.py
- test_prior.py
- test_queue.py
- messages.py
- Conflict
- test_repo_phase2_contracts.py
- test_health.py
- ТЗ фазы 2 — B2, требования, данные, тесты ИИ
- MisconceptionStateOut
- test_structured.py
- transport
- ТЗ фазы 2 — B3, платформа и API
- repo/texts.py
- test_migrations.py
- test_phase2_fixtures.py
- 6. Общие Pydantic-модели — дополнения к `app/schemas/`
- pick_template
- Ассистент подбора программ
- logging.py
- Фаза 2 — дельта контрактов
- words.py
- Репетитор
- knowledge/diagnostic.py
- 2. Требования, вехи, конфликты — `app/roadmap/`
- _FakeRedis
- _FakeRedis
- _FakeRedis
- 7. Сигнатуры функций между слоями
- 2. События
- schemas/health.py
- 3. Решения фазы
- 4. Соглашения — дополнения
- test_graph_pending_query_counts_unprocessed_last_hour
- test_matching_pipeline_limit_and_minimum
- 3. Данные в Postgres
- app/apply/__init__.py
- app/roadmap/__init__.py

## God Nodes (most connected - your core abstractions)
1. `RuleDeps` - 130 edges
2. `KnowledgeParams` - 122 edges
3. `EventType` - 98 edges
4. `NotFound` - 83 edges
5. `StudentCtx` - 72 edges
6. `Program` - 60 edges
7. `get_current_student()` - 59 edges
8. `LLMMessage` - 53 edges
9. `get_session()` - 51 edges
10. `Settings` - 51 edges

## Surprising Connections (you probably didn't know these)
- `2.1 `app/events/dispatch.py`` --references--> `RuleDeps`  [INFERRED]
  docs/tz/10-B3-phase2.md → app/events/dispatch.py
- `1. Что ты делаешь в этой фазе` --references--> `knowledge_version()`  [INFERRED]
  docs/tz/10-B3-phase2.md → app/keys.py
- `3.2 `assemble.py` — §10.1, product-logic §4.3` --references--> `due_at()`  [INFERRED]
  docs/tz/20-B1-phase2.md → app/knowledge/hlr.py
- `2.3 `roots.py`` --references--> `rule_root()`  [INFERRED]
  docs/tz/20-B1-phase2.md → app/knowledge/roots.py
- `3.1 `queue.py` — §10.1` --references--> `root_boost_skills()`  [INFERRED]
  docs/tz/20-B1-phase2.md → app/knowledge/roots.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Phase 1 Agent Prompt Files (v1)** — app_agents_prompts_selection_v1, app_agents_prompts_tutor_v1, app_agents_prompts_observer_v1, app_agents_prompts_extract_program_v1 [EXTRACTED 1.00]
- **B2 Sync-Log Contract Deviations** — docs_sync_log, concept_tool_read_only_param, concept_get_program_facts_naming, concept_loopend_naming_resolution, concept_observation_confidence_revision [EXTRACTED 1.00]
- **LLM Provider Decision Documentation Chain** — ssot_tech_stack, docs_tz_30_b2, docs_decisions_llm_provider, docs_tz_checklists_phase1_b2 [EXTRACTED 1.00]
- **Инструменты, доступные языковой модели (L2)** — backend_ssot_arch_logic_get_exam_format, backend_ssot_arch_logic_get_admission_route, backend_ssot_arch_logic_get_program_requirements, backend_ssot_arch_logic_save_profile_field, backend_ssot_arch_logic_run_program_search, backend_ssot_arch_logic_save_program, backend_ssot_arch_logic_get_skill_state [EXTRACTED 1.00]
- **Шесть слоёв архитектуры Quack (L1–L6)** — backend_ssot_arch_logic_l1_client, backend_ssot_arch_logic_l2_orchestration, backend_ssot_arch_logic_l3_ai_layer, backend_ssot_arch_logic_l4_deterministic_rules, backend_ssot_arch_logic_l5_data_storage, backend_ssot_arch_logic_l6_external_sources [EXTRACTED 1.00]
- **Конвейер доверия к свидетельствам (ярусы → Evidence → KnowledgeState через HLR)** — backend_ssot_memory_architecture_quack_trust_tiers, backend_ssot_memory_architecture_quack_evidence, backend_ssot_memory_architecture_quack_knowledgestate, backend_ssot_memory_architecture_quack_half_life_regression [INFERRED 0.85]

## Communities (184 total, 51 thin omitted)

### Community 0 - "KnowledgeParams"
Cohesion: 0.12
Nodes (36): KnowledgeParams, BaseModel, Parameter names, units and defaults from memory-architecture-quack.md §12., apply_evidence(), confidence(), 1 + 0.5 * alternation_rate. Empty list → 1.0., Apply one evidence to state, return a new state node. Starting state (state is…, Apply one evidence to half-life. direction=1 (correct): h *= (1 + alpha *… (+28 more)

### Community 1 - "repo/tasks.py"
Cohesion: 0.12
Nodes (36): SeenTemplate, TaskInstance, TaskTemplate, bump_seen(), get_answered_at(), get_instance(), get_seen(), get_seen_many() (+28 more)

### Community 2 - "repo/users.py"
Cohesion: 0.14
Nodes (21): hash_password(), verify_password(), User, get_user(), get_user_by_email(), AsyncSession, UUID, User persistence; transaction ownership remains with the caller. (+13 more)

### Community 3 - "canonical.py"
Cohesion: 0.06
Nodes (47): Приоры §4.8: слабое свидетельство + стартовое состояние по анкете. Пишем только…, _write_priors(), get_dependents(), get_exam_format(), get_prerequisites(), get_skill(), is_dag(), list_areas() (+39 more)

### Community 4 - "test_store_integration.py"
Cohesion: 0.13
Nodes (24): app_db, close_engine(), create_engine(), create_sessionmaker(), AsyncSession, Async PostgreSQL engine and session factories for API, seed and workers., Create an engine; connections are opened only when first used., Dispose the pool after callers have closed their sessions/connections. (+16 more)

### Community 5 - "errors.py"
Cohesion: 0.06
Nodes (43): Profile, apply_profile_update(), get_profile(), profile_readiness(), AsyncSession, UUID, Profile persistence and deterministic readiness calculation., AppError (+35 more)

### Community 6 - "config.py"
Cohesion: 0.08
Nodes (31): Application settings loaded from environment variables., optional_layer(), Any, Optional layer loading shared by the API and the workers. B1 (`app.graph.*`),…, Import `name`, or return None when that module itself is missing., app_search, extract_program(), Any (+23 more)

### Community 7 - "create_app"
Cohesion: 0.04
Nodes (49): app_api, issue_token(), UUID, app_events, knowledge_version(), create_app(), SavedProgram, fastapi_testclient (+41 more)

### Community 8 - "7. Применение — `app/apply/` (I/O)"
Cohesion: 0.08
Nodes (69): add_root_cause(), _dict_to_row(), ensure_student(), evidence_id(), get_state(), get_state_history(), get_states(), list_evidence() (+61 more)

### Community 9 - "events.py"
Cohesion: 0.12
Nodes (27): Transactional event append and read operations., DiagnosticCompletedPayload, DiagnosticProgressPayload, MessageAssistantPayload, MessageUserPayload, MilestoneDonePayload, MisconceptionDisputedPayload, MockCompletedPayload (+19 more)

### Community 10 - "kb.py"
Cohesion: 0.14
Nodes (20): _as_date(), get_admission_route(), list_facts_about(), list_requirements(), list_test_dates(), AsyncDriver, Read-only queries over the admission knowledge base (Neo4j). Source: memory-…, All routes for a country, each with requirements. (+12 more)

### Community 11 - "knowledge_base.py"
Cohesion: 0.18
Nodes (17): CountryRoutes, FactIn, AsyncDriver, BaseModel, Path, Load admission knowledge base — memory-architecture §2.3. Reads two files: -…, Neo4j doesn't allow mixed types — return None for list thresholds., Load exams.json (Fact nodes) and routes.json (Country–Route–Requirement). (+9 more)

### Community 12 - "StudentCtx"
Cohesion: 0.08
Nodes (52): get_current_student(), get_session(), AsyncSession, Commit a successful request and roll back a failed one., compare_matching(), get_matching(), _inputs(), AsyncSession (+44 more)

### Community 13 - "TaskTemplateSpec"
Cohesion: 0.14
Nodes (32): DistractorSpec, ParamSpec, TaskTemplateSpec, _build_mcq(), _build_multi_select(), _build_multi_select_traps(), _dummy_params(), _eval_or_literal() (+24 more)

### Community 14 - "test_evaluate.py"
Cohesion: 0.12
Nodes (29): check_constraints(), equal_values(), eval_expr(), Exception, Safe evaluation of template expressions — memory-architecture-quack.md §3.1. No…, True iff a and b are mathematically equal. Strings are compared as strings;…, Raised when a template expression is invalid, unsafe, or yields no value., Parse and evaluate a template expression. (+21 more)

### Community 15 - "keys.py"
Cohesion: 0.13
Nodes (9): current_session_id(), Redis, UUID, Redis-backed 30-minute student activity sessions., Frozen Redis key contract; pure key construction without Redis access., session(), FakeRedis, Redis activity-session behavior without a running Redis server. (+1 more)

### Community 16 - "Phase 1 Task Spec B2 (AI Layer)"
Cohesion: 0.15
Nodes (27): Extract Program Prompt v1, Observer Prompt v1, Selection Assistant Prompt v1, Selection Assistant Prompt v2, Tutor Prompt v1, LLM Circuit Breaker, backend/docs Ignored by .gitignore Issue, get_program_facts Naming Decision (+19 more)

### Community 17 - "selection.py"
Cohesion: 0.08
Nodes (49): AdmissionRouteArgs, compare(), CompareArgs, ExamFormatArgs, get_admission_route(), get_exam_format(), get_program_facts(), ProgramFactsArgs (+41 more)

### Community 18 - "profile_app"
Cohesion: 0.22
Nodes (3): profile_app(), ProfileSession, fixture

### Community 19 - "grade"
Cohesion: 0.20
Nodes (23): Option, grade(), Grade an answer against an instance. - mcq4/mcq5: answer is a key; correct →…, _mcq4(), _multi_select(), _numeric(), Answer grading — 20-B1.md §4.4, §7 (test_answer block)., Наблюдатель кладёт в obs.answer то, что написал ученик: число может прийти и… (+15 more)

### Community 20 - "test_misconceptions.py"
Cohesion: 0.08
Nodes (48): next_status(), datetime, Event, Misconception statuses, triggers, visibility — memory-architecture §5.1–§5.3.…, Short label for the student (§5.2)., §5.2 visibility table., Human phrase from triggers (§5.3). Only when n ≥ 3 and share ≥ 0.75., Transitions from §5.1. - None + hit → suspected - suspected + occurrence_count… (+40 more)

### Community 21 - "test_weights.py"
Cohesion: 0.14
Nodes (23): base_weight(), evidence_weight(), is_strong(), Tiers and weights for evidence — memory-architecture-quack.md §4.3, §8.1. Pure…, Tier 1 — mock/diagnostic; tier 2 — task, chat with a real solution; tier 3 —…, Base weight from the §4.3 table. Falls back to 0.0 for unknown combos., base * seen_template_factor (if repeated) * unmatched factor., Tiers 1 and 2 count as strong evidence; tier 3 does not. (+15 more)

### Community 22 - "LLMClient"
Cohesion: 0.09
Nodes (20): _decode(), LLMClient, build_tool_call(), LLMLike, Any, BaseModel, Exception, LLMStatus (+12 more)

### Community 23 - "FakeLLMClient"
Cohesion: 0.08
Nodes (39): AgentDeps, ChatKind, StreamEvent, Dependencies handed to every agent and, through it, every tool call.…, Stream a reply to one chat message. Phase 1 is echo-only: exactly two messages…, run_chat(), FakeCall, FakeLLMClient (+31 more)

### Community 24 - "EventType"
Cohesion: 0.17
Nodes (16): EventType, StrEnum, empty_registry(), _event_in(), FakeRedis, FakeSession, fixture, Event-store ordering, validation, and SQL contracts without live services. (+8 more)

### Community 25 - "postcheck.py"
Cohesion: 0.08
Nodes (41): check_facts(), _collect_result_values(), _extract_dates(), _extract_numbers(), _format_date(), _format_number(), _month_from_match(), _overlaps() (+33 more)

### Community 26 - "test_render.py"
Cohesion: 0.16
Nodes (20): _format_raw(), Any, Render template strings — memory-architecture-quack.md §3.1. - render_stem:…, Substitute {name} placeholders. Rule for parentheses: if a substituted value is…, Format a sympy value. Non-sympy values (str, tuple, list) are returned as their…, Render a raw param for embedding into a stem string., Rational → decimal string without trailing zeros., render_stem() (+12 more)

### Community 27 - "Settings"
Cohesion: 0.10
Nodes (23): model_validator, Задача с одним вызовом LLM на слоте chat плюс запас на I/O., Задача с одним вызовом LLM на слоте bulk плюс запас на I/O., An empty env value means "don't pass reasoning_effort at all", not the literal…, Infrastructure and application configuration, without service initialization., Settings, Redis, BaseSettings (+15 more)

### Community 28 - "LLMUnavailable"
Cohesion: 0.10
Nodes (29): Chat entrypoint — dispatches an incoming message to the right agent. Phase 1…, LLMUnavailable, load_prompt(), Prompt, Prompt loader with file-based versioning (docs/tz/30-B2.md §4.2). Prompts live…, argparse, dataclasses, Namespace (+21 more)

### Community 29 - "llm/client.py"
Cohesion: 0.09
Nodes (31): APIStatusError, APITimeoutError, app, llm_status(), LLM client contracts from the shared Phase 1 specification (00-contracts.md §6)., asyncio, openai, SimpleNamespace (+23 more)

### Community 30 - "test_data_schemas.py"
Cohesion: 0.23
Nodes (21): SkillsFile, _all_exam_format_files(), _all_misconception_files(), _all_skill_files(), _all_template_files(), _has_cycle(), dfs(), _load() (+13 more)

### Community 31 - "typing"
Cohesion: 0.05
Nodes (52): login(), logout(), me(), AsyncSession, Depends, get, post, Redis (+44 more)

### Community 32 - "api/chat.py"
Cohesion: 0.08
Nodes (43): StreamEvent, Drive one turn of the selection chat (product-logic §3.2). Stub for phase 1:…, run(), StreamEvent, Drive one turn of the prep chat (memory-architecture §9.4). Stub for phase 1:…, run(), _agent_router(), _chat_id() (+35 more)

### Community 33 - "repo/programs.py"
Cohesion: 0.16
Nodes (21): ProgramCache, SavedProgram, get_program(), list_all(), list_programs(), list_saved(), list_saved_programs(), AsyncSession (+13 more)

### Community 34 - "skills.py"
Cohesion: 0.19
Nodes (16): AreaDef, AreaSkillRef, ensure_schema(), ExamHeader, AsyncDriver, BaseModel, Path, Load skill map and areas into Neo4j — memory-architecture-quack.md §2.1.… (+8 more)

### Community 35 - "exam_formats.py"
Cohesion: 0.18
Nodes (14): _as_json(), ExamFormatFile, AsyncDriver, BaseModel, Path, Load exam formats (sections, scale table) into Neo4j — memory-architecture…, Load every .json under data/exam_formats/., Neo4j properties can't hold maps — store dict fields as JSON text.… (+6 more)

### Community 36 - "LLMMessage"
Cohesion: 0.17
Nodes (30): Every ``role="tool"`` message this client was ever called with. In a…, LoopEnd, ModelSlot, StreamEvent, Tool-calling loop: model -> tool call -> result back to model. Drives…, run_tool_loop(), _safe_json(), BaseModel (+22 more)

### Community 37 - "test_chat_sse.py"
Cohesion: 0.11
Nodes (16): Done, 3.5 Neo4j — новое в персональном слое, 2.2 `milestones.py` — product-logic §4.1, _events(), FakeSession, Chat transport tests with a fake implementation of the agreed B2 interface., _setup(), list_messages() (+8 more)

### Community 38 - "dispatch.py"
Cohesion: 0.14
Nodes (17): B1 misconception dispute — memory-architecture §5.1. I/O wrapper over…, B1 profile-updated apply — memory-architecture §4.8, product-logic §6.1. I/O…, apply_task_skipped(), AsyncSession, Task skipped / timed out — log only, no state change (§8.2)., Transactional Phase 2 event handler registry and dispatcher., The single Phase 2 event-to-B1-apply registration table., app_graph_queries (+9 more)

### Community 39 - "api/health.py"
Cohesion: 0.29
Nodes (13): _bounded_check(), _graph_pending(), health(), HealthOut, _llm_status(), _neo4j(), _postgres(), BaseModel (+5 more)

### Community 40 - "seed/misconceptions.py"
Cohesion: 0.10
Nodes (18): Embedder, Sentence embeddings — memory-architecture-quack.md §1.1, §5.4. Used only by…, Wrapper around sentence-transformers with lazy load and dimension check., Return L2-normalized embeddings, one per input text. Prefixes each text with…, app_graph, String constants for all Neo4j labels and relationship types. Source: memory-…, _load_catalog(), MisconceptionFileEntry (+10 more)

### Community 41 - "apply/knowledge.py"
Cohesion: 0.08
Nodes (36): explain(), _history(), misconceptions_view(), AsyncSession, ExamId, UUID, B1 knowledge read-models — memory-architecture §4.5, §5.2, §10.5. Read-only…, Visible-for-student misconception states across the exam's skills. (+28 more)

### Community 42 - "test_rank.py"
Cohesion: 0.13
Nodes (36): HardResult, BaseModel, Result of hard_filter for one program — memory-architecture §10.3., _priority_weights(), BaseModel, rank(), Ranked, Ranking within a realism level — product-logic §3.3, §5.3. Pure function:… (+28 more)

### Community 43 - "jobs.py"
Cohesion: 0.18
Nodes (14): extract_program(), observe_chat(), pregenerate_set(), propose_personal_nodes(), UUID, ARQ job stubs (docs/tz/30-B2.md §5.5). Signatures only: an ARQ worker context…, Extract observations from a chat window and reconcile them into the knowledge…, Pre-generate guidelines and explanations for every topic in a set so they're… (+6 more)

### Community 44 - "test_layers.py"
Cohesion: 0.27
Nodes (8): ast, _check_imports(), _imports(), parametrize, Path, Shared imports and Phase 2 layer boundaries., test_apply_does_not_import_llm_agents_or_fastapi(), test_phase2_pure_packages_do_not_import_io_layers()

### Community 45 - "pathlib"
Cohesion: 0.07
Nodes (26): app_seed, BaseModel, Path, seed_calendars(), TestDate, validate_calendars(), AsyncSession, Path (+18 more)

### Community 46 - "RuleDeps"
Cohesion: 0.09
Nodes (45): get_arq(), get_graph(), get_llm(), get_rule_deps(), Any, Request, ARQ pool for enqueuing jobs from a request, or None when unavailable., Use application-owned connections and a callable UTC clock. (+37 more)

### Community 47 - "pytest"
Cohesion: 0.23
Nodes (8): pytest, _deps(), empty_registry(), _event(), fixture, Handler registration order and failure propagation., test_handler_failure_stops_later_handlers(), test_handlers_run_once_in_registration_order()

### Community 48 - "Evidence (свидетельство)"
Cohesion: 0.18
Nodes (14): Модель знаний ученика, Evidence (свидетельство), explain_belief(node_id), get_learner_context(...), Half-life regression (модель забывания), KnowledgeState, Контекст репетитора (<learner_model>, §9), Канонизация персональных заблуждений (§5.4) (+6 more)

### Community 49 - "NotFound"
Cohesion: 0.22
Nodes (19): MockRun, complete_run(), create_run(), get_run(), Any, AsyncSession, UUID, Mock run persistence; answered progress lives on task instances. (+11 more)

### Community 50 - "apply/diagnostic.py"
Cohesion: 0.14
Nodes (38): active_diagnostic(), answer_diagnostic(), finish_diagnostic(), _out(), AsyncSession, Depends, ExamId, get (+30 more)

### Community 51 - "L2 Оркестрация / API"
Cohesion: 0.20
Nodes (12): Граф знаний о поступлении, get_admission_route, get_exam_format, get_program_requirements, get_skill_state, L1 Клиент, L2 Оркестрация / API, run_program_search (+4 more)

### Community 52 - "seed_templates"
Cohesion: 0.20
Nodes (10): _collect_trap_pairs(), AsyncDriver, AsyncSession, Path, Return [(distractor_key, misconception_id)] from all distractor sources., Validate all template files under path. Raises SeedError on first bad one.…, Walk data/templates/**/*.json and load each template. If session is given, also…, seed_templates() (+2 more)

### Community 53 - "test_hard.py"
Cohesion: 0.16
Nodes (37): hard_filter(), Score each program on its requirements vs the profile., Academics, Constraints, Direction, Level, Pace, Preferences (+29 more)

### Community 54 - "observer.py"
Cohesion: 0.18
Nodes (13): Observation, ObservationOut, observe(), Any, BaseModel, model_validator, Observer — output schema for the prep-chat observer (docs/tz/30-B2.md §5.4).…, Run the observer over one window of chat messages (phase 2). Not implemented in… (+5 more)

### Community 55 - "apply/mocks.py"
Cohesion: 0.12
Nodes (33): answer(), _find_section(), finish(), _minutes_for(), _pseudo_section(), AsyncSession, UUID, B1 mock-exam apply — memory-architecture §8.3, §10.2. I/O layer: assemble a… (+25 more)

### Community 56 - "test_sets.py"
Cohesion: 0.10
Nodes (23): on_program_change(), open_set(), program.saved / program.removed → rebuild both exams (cheap, safe)., Mark set as current; demote the previous current to upcoming (unless done).…, _deps(), _event(), _FakeRedis, _params() (+15 more)

### Community 57 - "3.4 Postgres — миграция `0002_phase2`"
Cohesion: 0.29
Nodes (4): 3.4 Postgres — миграция `0002_phase2`, parametrize, test_session_dependency_commits_or_rolls_back(), check()

### Community 58 - "build_topic_context"
Cohesion: 0.22
Nodes (10): build_topic_context(), AsyncDriver, BaseModel, UUID, Context assembler for the tutor agent (phase 2). Source: memory-architecture-…, Slots for the tutor's context block (memory-architecture §9.2). Each slot is a…, Phase 2: assemble the tutor context from 4 parallel Cypher queries. See memory-…, TopicContext (+2 more)

### Community 59 - "L3 ИИ / языковая модель"
Cohesion: 0.33
Nodes (9): Деградация по слоям (§6.3): таймаут, предгенерация, статус «недоступно», L3 ИИ / языковая модель, L4 Детерминированные правила, L5 Данные и хранилище, L6 Внешние источники, Реактивность: «изменил → изменилось» (§02), Правило §7: модель не источник правды, пишет только через инструменты L4, Всё, что можно посчитать правилом, считается правилом (+1 more)

### Community 60 - "generators.py"
Cohesion: 0.16
Nodes (11): Самопроверка перед ответом, Составитель шаблонов задач, Формат ответа, Что нужно сделать, Что подано на вход, _circle_chord(), generator(), Random (+3 more)

### Community 61 - "Profile"
Cohesion: 0.14
Nodes (29): _budget_factor(), _compare_above(), _compare_below(), _deadline_factor(), _exam_score_factor(), explain_empty(), _hint_for(), _language_factor() (+21 more)

### Community 62 - "ROOT_CAUSE"
Cohesion: 0.29
Nodes (7): Конфиг (§12, все параметры), Misconception (граф-узел, библиотечный+персональный), ROOT_CAUSE, Сборщик сетов (§10.1), Первичный замер (§4.2), Заблуждение (product-logic), Сеты (§4.3)

### Community 63 - "Свидетельство (product-logic)"
Cohesion: 0.29
Nodes (7): Ничего без доказательства (memory-architecture), Свидетельство (product-logic), Подборка (§3.3), Ничего без доказательства, Профиль, Оценка реалистичности, Два источника правды (профиль + действия)

### Community 64 - "apply/tasks.py"
Cohesion: 0.12
Nodes (24): issue(), AsyncSession, UUID, B1 task issuing — pick template, generate instance, record event. I/O layer:…, `task.issued.via` — где ученик получил задачу (00-contracts §5.2)., Pick a template for the requested skill/set and create one instance.…, _resolve_skill(), _to_out() (+16 more)

### Community 65 - "test_compare.py"
Cohesion: 0.21
Nodes (21): compare(), _differing_factors(), _factor_row(), _keyword_phrase(), _priority_row(), Comparison — product-logic §3.4, 20-B1-phase2.md §5.4. Pure function: build a…, Factor ids whose status differs across the compared programs., Side-by-side table across student-relevant and standard factors. (+13 more)

### Community 66 - "schemas/knowledge.py"
Cohesion: 0.08
Nodes (47): exam_progress(), B2 roadmap progress interface., Contract: 00-contracts-phase2.md §7.3., build_requirements(), _current_estimate(), ExamId, B2 roadmap requirement interface., Contract: 00-contracts-phase2.md §7.3. (+39 more)

### Community 67 - "reconcile.py"
Cohesion: 0.18
Nodes (19): app_knowledge, _apply_misconception(), _misc_name(), _p_from_self_level(), Reconcile a task answer — memory-architecture-quack.md §8.2, steps 2–8. Pure…, 1–5 → p_at_obs: ≥4 → 0.75, 3 → 0.5, ≤2 → 0.3., _tested_misconceptions(), MisconceptionChange (+11 more)

### Community 68 - "api/conftest.py"
Cohesion: 0.40
Nodes (4): app_llm, fixture, API unit tests use B2's fake client during the real application lifespan., use_fake_llm()

### Community 69 - "tasks/test_mocks.py"
Cohesion: 0.15
Nodes (30): Section, assemble_mock(), _pick_by_section(), _pick_generic(), _pick_misconception(), Random, Mock assembly and scoring — memory-architecture §8.3, §10.2. Pure functions:…, mock_set: cover item_types proportional to shares. (+22 more)

### Community 70 - "Сет"
Cohesion: 0.40
Nodes (5): Никакой лишней дисциплины, Рекомендации / Quack-лента (§3.6), Маршрут, Сет, Система рекомендует, ученик решает

### Community 71 - "env.py"
Cohesion: 0.15
Nodes (6): alembic, Alembic environment using the application async PostgreSQL settings., run_migrations_in_transaction(), run_migrations_online(), sqlalchemy_dialects, sys

### Community 72 - "Лог событий (events, Postgres)"
Cohesion: 0.50
Nodes (4): Лог событий (events, Postgres), Наблюдатель (чата подготовки), Replay (пересборка графа из событий), Чат подготовки (§4.5)

### Community 73 - "Карта навыков: канонический и персональный слои (§5.2)"
Cohesion: 0.67
Nodes (3): Каноническая карта навыков, Персональные узлы навыков, Карта навыков: канонический и персональный слои (§5.2)

### Community 74 - "Экземпляр задачи (TaskInstance, §3.3)"
Cohesion: 0.67
Nodes (3): Экземпляр задачи (TaskInstance, §3.3), Шаблон задачи (TaskTemplate, §3.1), Задачи и моки — датасет (§5.4)

### Community 75 - "Сохранённые (программы)"
Cohesion: 0.67
Nodes (3): Веха, Требование, Сохранённые (программы)

### Community 113 - "repo/sets.py"
Cohesion: 0.21
Nodes (29): Set, SetTopic, count_progress(), get_set(), list_sets(), _owned_set(), _planned_topics(), _project() (+21 more)

### Community 114 - "Program"
Cohesion: 0.15
Nodes (27): _exam_after_deadline(), _exclusive_rounds(), find_conflicts(), _has_document_requirement(), _is_binding(), date, ExamId, B2 roadmap conflict interface. (+19 more)

### Community 115 - "test_diagnostic_mocks_phase2.py"
Cohesion: 0.11
Nodes (22): DiagnosticResult, MockResultOut, BaseModel, _answer_result(), _async(), _diagnostic(), FakeRedis, FakeSession (+14 more)

### Community 116 - "test_sets_knowledge_phase2.py"
Cohesion: 0.14
Nodes (25): BaseModel, Phase 2 set and topic contracts., SetEditIn, SetOut, SetProgress, SetSwitchIn, TopicOut, 8. Роуты фазы 2 (B3) (+17 more)

### Community 117 - "schemas/tasks.py"
Cohesion: 0.16
Nodes (26): owned_instance(), AsyncSession, datetime, UUID, Shared task-answer recording for topic, diagnostic, and mock routes., Append once, dispatch once, and return the B1 handler's result., record_answer(), _session_minute() (+18 more)

### Community 118 - "knowledge/test_diagnostic.py"
Cohesion: 0.26
Nodes (28): apply_answer(), Advance the state after one answer. - correct → firm; prerequisites get…, Build the initial state: budget by area share, roots first in pending_descent., start(), AreaOut, _area(), _correct(), _prereq() (+20 more)

### Community 119 - "reconcile_task_answer"
Cohesion: 0.21
Nodes (27): ExamId, Apply one task answer (§8.2 steps 3–8). Steps 1 (event) and 9–10 (persistence,…, reconcile_task_answer(), _correct(), _instance(), _misc(), _partial(), _payload() (+19 more)

### Community 120 - "RootCauseOut"
Cohesion: 0.16
Nodes (26): diagnostic_root(), datetime, Root-cause rules — memory-architecture-quack.md §6, §10.1. Pure functions, no…, When an error is on a skill whose prerequisite is weak, point the root there.…, Root found by the diagnostic descent. Confidence 0.8, source 'diagnostic'., Skills that roots point to within root_window_days with Σ confidence ≥ 1.0.…, root_boost_skills(), rule_root() (+18 more)

### Community 121 - "test_assemble.py"
Cohesion: 0.15
Nodes (25): assemble_sets(), BaseModel, date, Assemble the roadmap of sets from a queue — memory-architecture §10.1. Pure…, One set in the roadmap — a plan to be persisted by repo.sets.replace_plan., Cut the queue into sets and give each a deadline. - set_size topics per set;…, _reason(), SetPlan (+17 more)

### Community 122 - "SkillWeight"
Cohesion: 0.14
Nodes (19): apply_dispute(), AsyncSession, Handle misconception.disputed / misconception.undisputed. Роутер уже записал…, SkillRef, SkillWeight, _deps(), _event(), _FakeRedis (+11 more)

### Community 123 - "ExamFormat"
Cohesion: 0.14
Nodes (24): p_target_for(), p_target_from(), AsyncSession, ExamId, UUID, Target recall per exam — p_target for queue, forecast and skill views.…, Inverse of `sets.forecast._scale` — scaled score back to raw points., Turn one exam target into the recall every skill of that exam aims at. (+16 more)

### Community 124 - "models.py"
Cohesion: 0.15
Nodes (24): Base, DailyAggregate, ForecastCache, MilestoneMark, PostgreSQL Phase 1 persistence schema., Recommendation, SetSummary, get() (+16 more)

### Community 125 - "tests/conftest.py"
Cohesion: 0.13
Nodes (23): close_driver(), create_driver(), AsyncDriver, Neo4j driver lifecycle — soft-fail wrapper. B3 connects this from…, Create an async Neo4j driver and verify connectivity. Returns None if the…, Close the driver. No-op if driver is None (graph was unavailable)., 9.3 Фикстуры conftest (B3, скелет), fakeredis_aioredis (+15 more)

### Community 126 - "test_task_answered.py"
Cohesion: 0.12
Nodes (14): _async(), _event(), _instance(), _params(), apply_task_answered — memory-architecture §8.2. Unit tests using monkeypatched…, Повторный dispatch того же task.answered не двигает счётчики. `bump_seen` и…, test_apply_is_idempotent_on_a_repeated_dispatch(), test_apply_missing_instance_returns_empty_result() (+6 more)

### Community 127 - "apply_task_answered"
Cohesion: 0.13
Nodes (20): _answer_result_without_state(), apply_task_answered(), Any, B1 task answer apply — memory-architecture §8.2, 11 steps. I/O layer: reads…, Steps 2–11 of §8.2 for one task.answered event. Step 1 (write event) and the…, bump(), get(), Redis (+12 more)

### Community 128 - "api/sets.py"
Cohesion: 0.29
Nodes (24): complete_topic(), edit_set(), get_set(), list_sets(), open_set(), open_topic(), _owned_set(), AsyncSession (+16 more)

### Community 129 - "test_phase2.py"
Cohesion: 0.12
Nodes (16): on(), Handler, importlib, _deps(), empty_registry(), _event(), fixture, parametrize (+8 more)

### Community 130 - "api/matching.py"
Cohesion: 0.12
Nodes (20): Phase 2 matching transport; B1 owns all selection rules., app_matching, brief(), Сжатая проекция результата подбора для контекста модели. Полный `MatchingOut` —…, `MatchingOut` -> компактный dict для `ToolPayload.model_data`., diff(), Detect shifts between two matchings — product-logic §3.3, §3.6. Pure function:…, One program whose realism or factors changed between two matchings. (+12 more)

### Community 131 - "test_profile_updated.py"
Cohesion: 0.16
Nodes (14): apply_profile_updated(), AsyncSession, При изменении ключевых полей профиля — пересобрать сеты всех экзаменов., _deps(), _event(), _FakeRedis, _params(), apply.profile_updated — 20-B1-phase2.md §7. (+6 more)

### Community 132 - "test_e2e_rules.py"
Cohesion: 0.11
Nodes (12): _client(), FakeRedis, fixture, E2E — сквозной сценарий шагов 4-8 product-logic через роутеры. Unit-транспорт:…, _skill_view(), _task_out(), test_step4_patch_profile_records_event(), test_step7_answer_task_bumps_knowledge() (+4 more)

### Community 133 - "ТЗ фазы 2 — B1, правила и граф"
Cohesion: 0.10
Nodes (20): next_skill(), Return the next skill to ask, or None if the run is done. Priority: reask_queue…, 0.1 Первый пуш: `phase2-b1-data` (60 минут, параллельно скелету B3, ничего не ждёт), 0. Сначала — что запушить сразу и чего ждать, 11. Вне скоупа, 2.3 `roots.py`, 2.4 `diagnostic.py` — §8.4, чистый автомат, 2.5 `hlr.py`, `weights.py` — без изменений, кроме (+12 more)

### Community 134 - "test_forecast.py"
Cohesion: 0.33
Nodes (20): forecast(), date, Build a ForecastOut from states and skill weights. - predicted_raw = Σ…, _format(), forecast — memory-architecture §4.7. Numbers from 20-B1-phase2.md §8…, _skill(), _state(), test_coverage_all_covered() (+12 more)

### Community 135 - "test_gen_templates.py"
Cohesion: 0.13
Nodes (10): importlib_util, redis_exceptions, _DownRedis, _FakeRedis, _load_module(), gen_templates.py skeleton (30-B2-phase2.md §0.1 п.2, §5)., test_generation_drops_invalid_template_and_writes_only_the_valid_one(), test_generation_drops_template_with_leftover_placeholder() (+2 more)

### Community 136 - "apply/test_diagnostic.py"
Cohesion: 0.15
Nodes (10): _deps(), _FakeRedis, _params(), apply.diagnostic — 20-B1-phase2.md §7., _skill(), test_finish_run_not_found(), fake_get(), test_start_graph_none_raises() (+2 more)

### Community 137 - "apply/sets.py"
Cohesion: 0.29
Nodes (16): _current_sets_by_exam(), _empty_sets_by_exam(), on_run_completed(), on_set_change(), AsyncSession, ExamId, UUID, B1 set apply — memory-architecture §10.1, apply contract §7.2. I/O layer:… (+8 more)

### Community 138 - "Event"
Cohesion: 0.22
Nodes (16): events(), Event, last_event_id(), list_by_type(), list_events(), list_unprocessed(), mark_processed(), AsyncSession (+8 more)

### Community 139 - "api/mocks.py"
Cohesion: 0.38
Nodes (15): answer_mock(), finish_mock(), get_mock(), _out(), AsyncSession, Depends, get, post (+7 more)

### Community 140 - "hlr.py"
Cohesion: 0.14
Nodes (15): difficulty_factor(), due_at(), datetime, Half-life regression formulas — memory-architecture-quack.md §4.1–4.2. Pure…, Moment when recall_p drops below p_target: last + h * log2(1/p_target)., P(recall now) = 2 ** (-Δt_h / half_life_h). Δt < 0 → 1.0., Normalize difficulty to [0.7, 1.3] linearly. difficulty=1 → 0.7, difficulty=max…, recall_p() (+7 more)

### Community 141 - "test_prior.py"
Cohesion: 0.36
Nodes (15): Convert one profile field into priors for skills without strong state., reconcile_prior(), _area(), reconcile_prior — memory-architecture §4.8., _skill(), test_invalid_value_type_returns_empty(), test_sat_score_same_as_ent(), test_self_assessment_does_not_override_strong_state() (+7 more)

### Community 142 - "test_queue.py"
Cohesion: 0.35
Nodes (15): build_queue(), Rank skills by need, prerequisites first. need = weight · gap · urgency ·…, build_queue — memory-architecture §10.1. Numbers from 20-B1-phase2.md §8…, _skill(), _state(), test_closed_skill_not_in_queue(), test_is_root_marks_skill(), test_need_formula_two_skills() (+7 more)

### Community 143 - "messages.py"
Cohesion: 0.23
Nodes (10): Message, append_message(), list_messages(), AsyncSession, UUID, Student-isolated chat read model., MessageSession, asyncio (+2 more)

### Community 144 - "Conflict"
Cohesion: 0.35
Nodes (14): complete_run(), create_run(), get_active_run(), _json(), _owned_run(), Any, AsyncSession, BaseModel (+6 more)

### Community 145 - "test_repo_phase2_contracts.py"
Cohesion: 0.16
Nodes (8): inspect, asyncio, parametrize, QuerySession, Import and frozen signature checks for Phase 2 repositories., test_list_all_excludes_flagged_programs(), test_personal_bulk_queries_filter_student_id(), test_phase2_repo_interfaces_are_async_and_session_first()

### Community 146 - "test_health.py"
Cohesion: 0.17
Nodes (10): no_pending_events(), count(), fixture, parametrize, Health, request middleware and log redaction contracts., test_graph_pending_is_recent_count_and_zero_is_omitted(), test_health_all_storage_ok(), healthy() (+2 more)

### Community 147 - "ТЗ фазы 2 — B2, требования, данные, тесты ИИ"
Cohesion: 0.14
Nodes (13): 0.1 Первый пуш: `phase2-b2-tests` (60 минут, параллельно скелету B3, ничего не ждёт), 0. Сначала — что запушить сразу и чего ждать, 1. Что ты делаешь в этой фазе, 3.1 Генератор — `scripts/gen_templates.py`, `app/agents/prompts/gen_template_v1.md`, 3.2 Шаблоны ЕНТ — `data/templates/ent/<area3>/`, 3.3 Библиотека заблуждений ЕНТ — `data/misconceptions/ent_*.json`, 3.4 Библиотека для репетитора, 3. Датасет (+5 more)

### Community 148 - "MisconceptionStateOut"
Cohesion: 0.21
Nodes (13): _find_state(), Найти состояние заблуждения по всем навыкам обоих экзаменов., get_misc_states(), _parse_triggers(), Misconception states for a set of skills — memory-architecture §5., Create or update MisconceptionState — memory-architecture §5. MERGE по…, upsert_misc_state(), MisconceptionStateOut (+5 more)

### Community 149 - "test_structured.py"
Cohesion: 0.26
Nodes (12): LLMResult, json, Foo, _make_response(), _make_tool_call(), BaseModel, Structured output: fence stripping, validation retry, tool mode…, test_first_invalid_second_valid_retries_and_records_validation_message() (+4 more)

### Community 150 - "transport"
Cohesion: 0.15
Nodes (4): FakeRedis, fixture, transport(), update_set()

### Community 151 - "ТЗ фазы 2 — B3, платформа и API"
Cohesion: 0.20
Nodes (9): Phase 2 access to the existing Phase 1 knowledge settings., 0.2 Чего ждать и когда, 0. Сначала — что запушить сразу и чего ждать, 1. Что ты делаешь в этой фазе, 5. CI и деплой, 7. Порядок подзадач (чтобы обрыв давал демо), 8. Приёмка фазы, 9. Вне скоупа (+1 more)

### Community 152 - "repo/texts.py"
Cohesion: 0.33
Nodes (9): GeneratedText, get_generated(), put_generated(), AsyncSession, Generated text cache keyed by kind and input hash., _to_schema(), GeneratedText, BaseModel (+1 more)

### Community 153 - "test_migrations.py"
Cohesion: 0.25
Nodes (10): CompletedProcess, sqlalchemy_engine, _alembic(), _inspect_database(), integration, Phase 1 and Phase 2 schema and migration checks., test_metadata_has_phase1_and_phase2_tables_and_constraints(), test_offline_downgrade_removes_only_phase2_schema() (+2 more)

### Community 154 - "test_phase2_fixtures.py"
Cohesion: 0.24
Nodes (8): app_apply, integration, Phase 2 fixture data and dependency setup without external services., test_fake_apply_patches_only_test_target(), test_fake_apply_replaces_registered_handler(), test_seeded_graph_fixture(), test_student_with_saved_fixture(), test_templates_db_fixture()

### Community 155 - "6. Общие Pydantic-модели — дополнения к `app/schemas/`"
Cohesion: 0.20
Nodes (10): 6. Общие Pydantic-модели — дополнения к `app/schemas/`, `common.py`, `diagnostic.py` — memory-architecture §8.4, `events.py` — payload-модели фазы 2, `knowledge.py` — дополнения, `matching.py` — product-logic §3.3–§3.4, `mocks.py` — memory-architecture §8.3, §10.2, `roadmap.py` — product-logic §3.5, §4.1 (+2 more)

### Community 156 - "pick_template"
Cohesion: 0.31
Nodes (8): pick_template(), Random, Template selection for one skill — memory-architecture §10.2. Pure function:…, Choose one template from the pool. Rules (§10.2): - prefer templates with…, Убираем суффикс после последнего '_' — структура без параметров., 1 — шаг вверх, -1 — шаг вниз, 0 — стартовая (медиана)., _skeleton(), _target_difficulty()

### Community 157 - "Ассистент подбора программ"
Cohesion: 0.25
Nodes (7): Ассистент подбора программ, Границы и привычки, Жёсткое правило про числа, Инструменты, Реалистичность, Типы реплик, Ход разговора

### Community 158 - "logging.py"
Cohesion: 0.36
Nodes (7): configure_logging(), mask_secrets(), _mask_value(), Any, Structured JSON logging with request context and secret masking., Redact secret-bearing fields, including nested structured fields., test_log_processor_masks_nested_secret_keys()

### Community 159 - "Фаза 2 — дельта контрактов"
Cohesion: 0.25
Nodes (7): 10. Вне фазы, 1. Что такое фаза 2, 5. Параметры — дополнения к `KnowledgeParams`, 9.2 Кто чего ждёт, 9.4 Порядок фазы, 9. Точки стыка и порядок, Фаза 2 — дельта контрактов

### Community 160 - "words.py"
Cohesion: 0.33
Nodes (6): Human-facing words for skill states — memory-architecture §4.5, §4.7. Pure…, One word per state, same thresholds everywhere. - no state or confidence <…, Short phrase for messages: '<навык>: шатко → уверенно' style., skill_level(), state_words(), SkillLevel

### Community 161 - "Репетитор"
Cohesion: 0.33
Nodes (5): policy, Границы, Инструменты (только чтение), Модель ученика, Репетитор

### Community 162 - "knowledge/diagnostic.py"
Cohesion: 0.40
Nodes (5): finish(), _make_uuid(), Diagnostic — adaptive descent by prerequisites — memory-architecture §8.4. Pure…, Final result: firm / shaky / roots / suspected / start_from + words., _words()

### Community 163 - "2. Требования, вехи, конфликты — `app/roadmap/`"
Cohesion: 0.33
Nodes (6): 2.1 `requirements.py` — product-logic §4.1, дельта §3.3, 2.3 `conflicts.py` — product-logic §3.5, 2.4 `progress.py` — product-logic §4.1, 2.5 Слова, 2. Требования, вехи, конфликты — `app/roadmap/`, text()

### Community 167 - "7. Сигнатуры функций между слоями"
Cohesion: 0.40
Nodes (5): 7.1 B1 — чистые (`knowledge/`, `sets/`, `matching/`, `tasks/`), 7.2 B1 — с I/O (`apply/`, `graph/queries/personal.py`), 7.3 B2 — чистые (`roadmap/`), 7.4 B3 — репозитории и события, 7. Сигнатуры функций между слоями

### Community 168 - "2. События"
Cohesion: 0.40
Nodes (5): 2.1 `app/events/dispatch.py`, 2.2 `app/events/handlers.py` — единственный реестр, 2.3 `app/events/version.py`, 2.4 `app/events/store.py`, 2. События

### Community 169 - "schemas/health.py"
Cohesion: 0.50
Nodes (3): HealthOut, BaseModel, Health-check contract from the shared Phase 1 specification (00-contracts.md…

### Community 170 - "3. Решения фазы"
Cohesion: 0.50
Nodes (4): 3.2 Где лежат сеты, замер, моки, вехи, 3.3 Целевой балл и цель по навыку, 3.6 Датасет фазы, 3. Решения фазы

### Community 171 - "4. Соглашения — дополнения"
Cohesion: 0.50
Nodes (4): 4.2 HTTP — новые правила, 4.3 Уровни реалистичности и статусы — словами, 4.4 Redis — новые ключи (`app/keys.py`, B3), 4. Соглашения — дополнения

### Community 174 - "3. Данные в Postgres"
Cohesion: 0.67
Nodes (3): 3.1 Модели и миграция, 3.3 Данные — `data/`, 3. Данные в Postgres

## Ambiguous Edges - Review These
- `B1 Phase 1 Report (Engine and Graph)` → `Phase 1 Shared Contracts`  [AMBIGUOUS]
  docs/B1.md · relation: conceptually_related_to
- `Phase 1 Shared Contracts` → `Quack Backend README`  [AMBIGUOUS]
  README.md · relation: references

## Knowledge Gaps
- **80 isolated node(s):** `WorkerInteractive`, `WorkerBulk`, `quack-api`, `Что подано на вход`, `Что нужно сделать` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1103 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `B1 Phase 1 Report (Engine and Graph)` and `Phase 1 Shared Contracts`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Phase 1 Shared Contracts` and `Quack Backend README`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `KnowledgeParams` connect `KnowledgeParams` to `test_phase2.py`, `test_profile_updated.py`, `test_e2e_rules.py`, `ТЗ фазы 2 — B1, правила и граф`, `config.py`, `test_forecast.py`, `7. Применение — `app/apply/` (I/O)`, `create_app`, `events.py`, `apply/test_diagnostic.py`, `hlr.py`, `test_prior.py`, `test_queue.py`, `test_misconceptions.py`, `test_weights.py`, `transport`, `ТЗ фазы 2 — B3, платформа и API`, `Фаза 2 — дельта контрактов`, `words.py`, `knowledge/diagnostic.py`, `dispatch.py`, `apply/knowledge.py`, `test_rank.py`, `RuleDeps`, `pytest`, `test_hard.py`, `apply/mocks.py`, `test_sets.py`, `Profile`, `apply/tasks.py`, `schemas/knowledge.py`, `reconcile.py`, `tasks/test_mocks.py`, `test_diagnostic_mocks_phase2.py`, `test_sets_knowledge_phase2.py`, `knowledge/test_diagnostic.py`, `reconcile_task_answer`, `RootCauseOut`, `test_assemble.py`, `SkillWeight`, `ExamFormat`, `tests/conftest.py`, `test_task_answered.py`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `RuleDeps` connect `RuleDeps` to `api/sets.py`, `KnowledgeParams`, `api/matching.py`, `test_profile_updated.py`, `canonical.py`, `test_e2e_rules.py`, `repo/tasks.py`, `create_app`, `apply/test_diagnostic.py`, `apply/sets.py`, `events.py`, `api/mocks.py`, `StudentCtx`, `test_phase2.py`, `MisconceptionStateOut`, `transport`, `typing`, `Фаза 2 — дельта контрактов`, `dispatch.py`, `2. События`, `apply/knowledge.py`, `pytest`, `apply/diagnostic.py`, `apply/mocks.py`, `test_sets.py`, `Profile`, `apply/tasks.py`, `schemas/knowledge.py`, `test_diagnostic_mocks_phase2.py`, `test_sets_knowledge_phase2.py`, `schemas/tasks.py`, `test_assemble.py`, `SkillWeight`, `ExamFormat`, `tests/conftest.py`, `test_task_answered.py`, `apply_task_answered`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `EventType` connect `EventType` to `api/sets.py`, `test_phase2.py`, `test_profile_updated.py`, `test_store_integration.py`, `create_app`, `apply/sets.py`, `events.py`, `Event`, `StudentCtx`, `test_phase2_fixtures.py`, `typing`, `api/chat.py`, `dispatch.py`, `RuleDeps`, `pytest`, `apply/diagnostic.py`, `apply/mocks.py`, `test_sets.py`, `apply/tasks.py`, `schemas/tasks.py`, `SkillWeight`, `test_task_answered.py`, `apply_task_answered`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Are the 80 inferred relationships involving `RuleDeps` (e.g. with `record_answer()` and `active_diagnostic()`) actually correct?**
  _`RuleDeps` has 80 INFERRED edges - model-reasoned connections that need verification._
- **Are the 47 inferred relationships involving `KnowledgeParams` (e.g. with `p_target_from()` and `RuleDeps`) actually correct?**
  _`KnowledgeParams` has 47 INFERRED edges - model-reasoned connections that need verification._