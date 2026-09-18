# Graph Report - backend  (2026-09-18)

## Corpus Check
- 122 files · ~59,917 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1147 nodes · 2454 edges · 96 communities (68 shown, 28 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 202 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `47c9f6a2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_API Orchestration & Tool Registry|API Orchestration & Tool Registry]]
- [[_COMMUNITY_Learner Knowledge & Misconception State|Learner Knowledge & Misconception State]]
- [[_COMMUNITY_Profile & Evidence-Based Claims|Profile & Evidence-Based Claims]]
- [[_COMMUNITY_Chat, LLM & Streaming Infra|Chat, LLM & Streaming Infra]]
- [[_COMMUNITY_Six-Layer Architecture & Deterministic Rules|Six-Layer Architecture & Deterministic Rules]]
- [[_COMMUNITY_SkillMisconception Graph & Sets|Skill/Misconception Graph & Sets]]
- [[_COMMUNITY_Recommendations & Student Autonomy|Recommendations & Student Autonomy]]
- [[_COMMUNITY_Task Templates & Sympy Evaluation|Task Templates & Sympy Evaluation]]
- [[_COMMUNITY_Canonical Skill Mapping|Canonical Skill Mapping]]
- [[_COMMUNITY_Exam Calendars|Exam Calendars]]
- [[_COMMUNITY_Program Cache|Program Cache]]
- [[_COMMUNITY_Thesis Events as Source of Truth|Thesis: Events as Source of Truth]]
- [[_COMMUNITY_Thesis Tutor vs Observer|Thesis: Tutor vs Observer]]
- [[_COMMUNITY_Program Comparison|Program Comparison]]
- [[_COMMUNITY_Exam Format|Exam Format]]
- [[_COMMUNITY_Overview Tab|Overview Tab]]
- [[_COMMUNITY_Program Entity|Program Entity]]
- [[_COMMUNITY_Program Web Search Cache|Program Web Search Cache]]
- [[_COMMUNITY_FastAPI Backend|FastAPI Backend]]
- [[_COMMUNITY_Next.js Frontend (tech-stack ref)|Next.js Frontend (tech-stack ref)]]
- [[_COMMUNITY_Redis|Redis]]
- [[_COMMUNITY_Tavily Search|Tavily Search]]
- [[_COMMUNITY_VPS Deploy|VPS Deploy]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 91|Community 91]]

## God Nodes (most connected - your core abstractions)
1. `LLMClient` - 35 edges
2. `LLMMessage` - 34 edges
3. `ToolCtx` - 29 edges
4. `AgentDeps` - 28 edges
5. `StudentCtx` - 25 edges
6. `Profile` - 24 edges
7. `Program` - 24 edges
8. `SeedError` - 24 edges
9. `LLMUnavailable` - 23 edges
10. `LLMLike` - 23 edges

## Surprising Connections (you probably didn't know these)
- `API / Оркестрация (backend)` --conceptually_related_to--> `Профиль`  [INFERRED]
  README.md → ssot/product-logic.md
- `EchoProbeRun` --uses--> `ObservationOut`  [INFERRED]
  scripts/llm_probe.py → app/agents/observer.py
- `StreamProbeResult` --uses--> `ObservationOut`  [INFERRED]
  scripts/llm_probe.py → app/agents/observer.py
- `StructuredProbeResult` --uses--> `ObservationOut`  [INFERRED]
  scripts/llm_probe.py → app/agents/observer.py
- `EchoProbeRun` --uses--> `Settings`  [INFERRED]
  scripts/llm_probe.py → app/config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Инструменты, доступные языковой модели (L2)** — backend_ssot_arch_logic_get_exam_format, backend_ssot_arch_logic_get_admission_route, backend_ssot_arch_logic_get_program_requirements, backend_ssot_arch_logic_save_profile_field, backend_ssot_arch_logic_run_program_search, backend_ssot_arch_logic_save_program, backend_ssot_arch_logic_get_skill_state [EXTRACTED 1.00]
- **Шесть слоёв архитектуры Quack (L1–L6)** — backend_ssot_arch_logic_l1_client, backend_ssot_arch_logic_l2_orchestration, backend_ssot_arch_logic_l3_ai_layer, backend_ssot_arch_logic_l4_deterministic_rules, backend_ssot_arch_logic_l5_data_storage, backend_ssot_arch_logic_l6_external_sources [EXTRACTED 1.00]
- **Конвейер доверия к свидетельствам (ярусы → Evidence → KnowledgeState через HLR)** — backend_ssot_memory_architecture_quack_trust_tiers, backend_ssot_memory_architecture_quack_evidence, backend_ssot_memory_architecture_quack_knowledgestate, backend_ssot_memory_architecture_quack_half_life_regression [INFERRED 0.85]

## Communities (96 total, 28 thin omitted)

### Community 0 - "API Orchestration & Tool Registry"
Cohesion: 0.18
Nodes (19): ИИ-слой (backend README), API / Оркестрация (backend), get_admission_route, get_exam_format, get_program_requirements, get_skill_state, L1 Клиент, L2 Оркестрация / API (+11 more)

### Community 1 - "Learner Knowledge & Misconception State"
Cohesion: 0.12
Nodes (20): Модель знаний ученика, Конфиг (§12, все параметры), Evidence (свидетельство), explain_belief(node_id), get_learner_context(...), Half-life regression (модель забывания), KnowledgeState, Контекст репетитора (<learner_model>, §9) (+12 more)

### Community 2 - "Profile & Evidence-Based Claims"
Cohesion: 0.22
Nodes (9): frontend localStorage, frontend programs.ts, Ничего без доказательства (memory-architecture), Свидетельство (product-logic), Подборка (§3.3), Ничего без доказательства, Профиль, Оценка реалистичности (+1 more)

### Community 3 - "Chat, LLM & Streaming Infra"
Cohesion: 0.17
Nodes (12): frontend assistant.ts, Лог событий (events, Postgres), Наблюдатель (чата подготовки), Replay (пересборка графа из событий), Чат подбора (§3.2), Чат подготовки (§4.5), ARQ (фоновые задачи, 2 очереди), LLM-провайдер (OpenAI-совместимый API) (+4 more)

### Community 4 - "Six-Layer Architecture & Deterministic Rules"
Cohesion: 0.29
Nodes (10): Детерминированные правила (backend README), Деградация по слоям (§6.3): таймаут, предгенерация, статус «недоступно», L3 ИИ / языковая модель, L4 Детерминированные правила, L5 Данные и хранилище, L6 Внешние источники, Реактивность: «изменил → изменилось» (§02), Правило §7: модель не источник правды, пишет только через инструменты L4 (+2 more)

### Community 5 - "Skill/Misconception Graph & Sets"
Cohesion: 0.29
Nodes (7): Misconception (граф-узел, библиотечный+персональный), Skill (граф-узел, канонический+персональный), Текущий сет (§4.4), Первичный замер (§4.2), Заблуждение (product-logic), Навык (product-logic), Neo4j 5 Community

### Community 6 - "Recommendations & Student Autonomy"
Cohesion: 0.40
Nodes (5): Никакой лишней дисциплины, Рекомендации / Quack-лента (§3.6), Маршрут, Сет, Система рекомендует, ученик решает

### Community 7 - "Task Templates & Sympy Evaluation"
Cohesion: 0.06
Nodes (60): Observation, ObservationOut, observe(), Observer — output schema for the prep-chat observer (docs/tz/30-B2.md §5.4)., Run the observer over one window of chat messages (phase 2).      Not implemen, Infrastructure and application configuration, without service initialization., An empty env value means "don't pass reasoning_effort at all",         not the, Settings (+52 more)

### Community 8 - "Canonical Skill Mapping"
Cohesion: 0.67
Nodes (3): Каноническая карта навыков, Персональные узлы навыков, Карта навыков: канонический и персональный слои (§5.2)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (48): AgentDeps, Chat entrypoint — dispatches an incoming message to the right agent.  Phase 1, Dependencies handed to every agent and, through it, every tool call.      Cons, Stream a reply to one chat message.      Phase 1 is echo-only: exactly two mes, run_chat(), AdmissionRouteArgs, compare(), CompareArgs (+40 more)

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (48): Random, AnswerIn, AnswerResult, DistractorSpec, OmissionTrap, Option, ParamSpec, Task persistence contracts from the shared Phase 1 specification. (+40 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (42): Base, DailyAggregate, Event, GeneratedText, Message, Profile, ProgramCache, PostgreSQL Phase 1 persistence schema. (+34 more)

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (29): Alembic environment using the application async PostgreSQL settings., run_migrations_in_transaction(), run_migrations_online(), configure_logging(), mask_secrets(), _mask_value(), Structured JSON logging with request context and secret masking., Redact secret-bearing fields, including nested structured fields. (+21 more)

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (30): SearchUnavailable, ValidationFailed, compare(), Comparison, Comparison — product-logic §3.4. Phase 2 stub., Phase 2: side-by-side table across student-relevant and standard factors., hard_filter(), HardResult (+22 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (32): AsyncDriver, close_driver(), Close the driver. No-op if driver is None (graph was unavailable)., get_dependents(), get_exam_format(), get_prerequisites(), get_skill(), is_dag() (+24 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (33): 1\. Что такое фаза 1, 2\. Репозиторий и владение, 3.1 Вход и учётные записи, 3.2 Безопасность — что обязательно в фазе 1, 3.3 Сессия работы ученика, 3.4 Postgres — вся схема сейчас, 3.5 Neo4j, 3.6 Языковая модель (+25 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (28): _agent_router(), Authenticated chat transport; agent behavior belongs to B2., Import the agreed B2 interface, without a production fallback agent., _wrap_agent(), AsyncSession, Event, dispatch(), on() (+20 more)

### Community 31 - "Community 31"
Cohesion: 0.10
Nodes (30): datetime, apply_evidence(), confidence(), difficulty_factor(), due_at(), Half-life regression formulas — memory-architecture-quack.md §4.1–4.2.  Pure f, 1 + 0.5 * alternation_rate. Empty list → 1.0., Moment when recall_p drops below p_target: last + h * log2(1/p_target). (+22 more)

### Community 32 - "Community 32"
Cohesion: 0.06
Nodes (30): 0\. Обзор, 1\. Фронтенд `[F1, F2]`, 2.1 Структура, 2.2 Ключевые библиотеки, 2.3 Аутентификация, 2.4 Чат и стриминг, 2.5 Фоновые задачи — ARQ, две очереди `[B3]`, 2\. Бэкенд `[B1, B2]` (+22 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (23): Authenticated program-cache read routes., list_saved(), Authenticated saved-program routes., SavedProgramWithProgram, NotFound, get_program(), list_programs(), list_saved() (+15 more)

### Community 34 - "Community 34"
Cohesion: 0.14
Nodes (22): KnowledgeParams, Application settings loaded from environment variables., Parameter names, units and defaults from memory-architecture-quack.md §12., next_status(), Misconception status logic — memory-architecture-quack.md §5.1–5.3.  Phase 1:, Phase 2: transitions from §5.1 (suspected → confirmed → resolved).      Rules:, Phase 2: aggregate triggers from evidence contexts (§5.3).      Returns a dict, update_triggers() (+14 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (26): 1\. Что ты делаешь в этой фазе, 2\. Выбор провайдера — первая задача, до кода, 3.1 Интерфейс, 3.2 Транспорт, 3.3 Rate-limit, 3.4 Circuit breaker и статус — tech-stack §4.7, 3.5 Structured output — tech-stack §4.2, 3.6 Фейк — `app/llm/fake.py` (+18 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (24): extract_program(), observe_chat(), pregenerate_set(), propose_personal_nodes(), ARQ job stubs (docs/tz/30-B2.md §5.5).  Signatures only: an ARQ worker context, Extract observations from a chat window and reconcile them into the     knowled, Pre-generate guidelines and explanations for every topic in a set so     they'r, Build the short end-of-set report — what's closed, which skills     firmed up, (+16 more)

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (22): Path, _as_json(), ExamFormatFile, Load exam formats (sections, scale table) into Neo4j — memory-architecture §2.3., Load every .json under data/exam_formats/., Neo4j properties can't hold maps — store dict fields as JSON text.      canoni, SectionDef, seed_exam_formats() (+14 more)

### Community 38 - "Community 38"
Cohesion: 0.08
Nodes (25): 0\. Шапка, 1\. Пользователь, 2\. Продукт целиком, 3.1 Профиль, 3.2 Чат подбора, 3.3 Подборка, 3.4 Сравнение\[ДОРАБОТАТЬ\!\], 3.5 Сохраненные (+17 more)

### Community 39 - "Community 39"
Cohesion: 0.14
Nodes (21): get_current_student(), get_graph(), get_llm(), get_redis(), get_session(), FastAPI dependencies for infrastructure and authenticated students., Commit a successful request and roll back a failed one., _bounded_check() (+13 more)

### Community 40 - "Community 40"
Cohesion: 0.23
Nodes (24): logout(), me(), _chat_id(), get_messages(), post_message(), get_knowledge_version(), KnowledgeVersionOut, get_profile() (+16 more)

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (17): BaseModel, HealthOut, Health-check contract from the shared Phase 1 specification (00-contracts.md §6), EvidenceContext, Academics, Constraints, Direction, Level (+9 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (15): issue_token(), login(), Cookie-based student authentication., client_ip(), AppError, Conflict, Forbidden, Frozen application error contract. (+7 more)

### Community 43 - "Community 43"
Cohesion: 0.25
Nodes (15): check_facts(), _collect_result_values(), _extract_dates(), _extract_numbers(), _format_date(), _format_number(), _month_from_match(), _overlaps() (+7 more)

### Community 44 - "Community 44"
Cohesion: 0.27
Nodes (13): hash_password(), verify_password(), User, get_user(), get_user_by_email(), User persistence; transaction ownership remains with the caller., _to_row(), upsert_user() (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.14
Nodes (13): 1. `structured()` с `ObservationOut`, 2. `stream()` с инструментом `get_time`, 3. Лимиты аккаунта, Вердикт по критериям приёмки §2, Кандидаты, Отклонение от бюджета, Пересмотр, Почему не Kimi K3 основным (+5 more)

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (13): get_admission_route(), list_facts_about(), list_requirements(), list_test_dates(), Read-only queries over the admission knowledge base (Neo4j).  Source: memory-a, All routes for a country, each with requirements., Program requirements — read from Postgres in the real path.      Program nodes, TestDate nodes attached to an Exam, ordered by date. (+5 more)

### Community 47 - "Community 47"
Cohesion: 0.21
Nodes (8): Embedder, Sentence embeddings — memory-architecture-quack.md §1.1, §5.4.  Used only by s, Wrapper around sentence-transformers with lazy load and dimension check., Return L2-normalized embeddings, one per input text.          Prefixes each te, MisconceptionFileEntry, Load the misconception library into Neo4j — memory-architecture §5.4.  Each li, Load data/misconceptions/library.json into Neo4j., seed_misconceptions()

### Community 48 - "Community 48"
Cohesion: 0.21
Nodes (12): AreaDef, AreaSkillRef, ExamHeader, Load skill map and areas into Neo4j — memory-architecture-quack.md §2.1.  Idem, Load skills from data/skills/. Exam + Area + Skill + all relations., seed_skills(), SkillDef, SkillRequires (+4 more)

### Community 49 - "Community 49"
Cohesion: 0.20
Nodes (4): Frozen Redis key contract; pure key construction without Redis access., session(), current_session_id(), Redis-backed 30-minute student activity sessions.

### Community 50 - "Community 50"
Cohesion: 0.17
Nodes (11): 0.1 Словарь (дополнение к §0 product-logic), 0\. Тезисы, 12\. Конфиг — все параметры в одном месте, 13\. Открытые вопросы, 1.1 Что где лежит, 1.2 Лог событий, 1\. Хранилища и слои, 6\. Корни ошибок — `ROOT_CAUSE` (+3 more)

### Community 51 - "Community 51"
Cohesion: 0.18
Nodes (10): B1 — движок и граф, Граф Neo4j — `backend/app/graph/`, Данные — `data/`, Загрузчики в граф — `backend/app/seed/`, Задачи из шаблонов — `backend/app/tasks/`, Правила — `backend/app/knowledge/`, Тесты, Формат данных — `docs/data-formats.md` (+2 more)

### Community 52 - "Community 52"
Cohesion: 0.22
Nodes (10): base_weight(), evidence_weight(), is_strong(), Tiers and weights for evidence — memory-architecture-quack.md §4.3, §8.1.  Pur, Tier 1 — mock/diagnostic; tier 2 — task, chat with a real solution;     tier 3, Base weight from the §4.3 table. Falls back to 0.0 for unknown combos., base * seen_template_factor (if repeated) * unmatched factor., Tiers 1 and 2 count as strong evidence; tier 3 does not. (+2 more)

### Community 53 - "Community 53"
Cohesion: 0.22
Nodes (8): String constants for all Neo4j labels and relationship types.  Source: memory-, _collect_trap_pairs(), Load task templates into Neo4j and Postgres cache — memory-architecture §3.1., Return [(distractor_key, misconception_id)] from all distractor sources., Validate all template files under path. Raises SeedError on first bad one., Walk data/templates/**/*.json and load each template.      If session is given, seed_templates(), validate_templates()

### Community 54 - "Community 54"
Cohesion: 0.20
Nodes (9): Границы, Задачи в разговоре, Инструменты (только чтение), Как обращаться с заблуждениями, Корневые причины и сильные стороны, Подсказки, Режим по последнему сообщению ученика, Репетитор (+1 more)

### Community 55 - "Community 55"
Cohesion: 0.22
Nodes (9): 4.1 Модель забывания — half-life regression, 4.2 Уверенность, 4.3 Ярусы доверия, 4.4 Цель, 4.5 Закрыт / разрыв / повторение, 4.6 Общие навыки двух экзаменов, 4.7 Прогнозный балл и покрытие, 4.8 Приоры из анкеты (+1 more)

### Community 56 - "Community 56"
Cohesion: 0.22
Nodes (9): 8.1 Чат подготовки — наблюдатель (L → R), 8.2 Задачи (R), 8.3 Моки (R), 8.4 Замер (R с очередью), 8.5 Анкета (R), 8.6 Персональные заблуждения — §5.4., 8.7 Персональные узлы (L → R) при `set.opened`, 8.8 Replay (+1 more)

### Community 57 - "Community 57"
Cohesion: 0.29
Nodes (7): apply_schema(), _load_statements(), Apply the Neo4j schema (indices, constraints) idempotently.  Called by seed_sk, Read schema.cypher, split by ';', substitute $dim, drop comments/empties., Run all schema statements sequentially. Idempotent., ensure_schema(), Convenience wrapper — call apply_schema before the first seed_skills.

### Community 58 - "Community 58"
Cohesion: 0.25
Nodes (8): 10.1 Сборщик сетов `[B1]`, 10.2 Выбор задачи и сборка моков `[B1]`, 10.3 Прогнозный балл и реалистичность `[B1 → B2]`, 10.4 Отчёт по сету `[B2]`, 10.5 «Почему так считаешь» `[F2]`, 10.6 Ассистент подбора `[B2]`, 10.7 Профиль ученика (procedural), 10\. Потребители модели знаний

### Community 59 - "Community 59"
Cohesion: 0.29
Nodes (6): Ассистент подбора программ, Главная задача — понять человека, а не заполнить анкету, Жёсткие ограничения, После изменений, Типы реплик ученика, Ход разговора

### Community 60 - "Community 60"
Cohesion: 0.29
Nodes (7): 3.1 Шаблон, 3.2 Ручные задачи, 3.3 Экземпляр, 3.4 Инварианты — проверяются автоматически при генерации, 3.5 Откуда шаблоны, 3.6 Пул и повторы, 3\. Задачи: шаблоны и ручные задачи `[B2 схема и слияние, все пишут]`

### Community 61 - "Community 61"
Cohesion: 0.33
Nodes (6): Данные (backend README слой), Граф знаний о поступлении, Датасет задач (arch-logic), Веха, Требование, Сохранённые (программы)

### Community 62 - "Community 62"
Cohesion: 0.40
Nodes (5): build_topic_context(), Context assembler for the tutor agent (phase 2).  Source: memory-architecture-, Slots for the tutor's context block (memory-architecture §9.2).      Each slot, Phase 2: assemble the tutor context from 4 parallel Cypher queries.      See m, TopicContext

### Community 63 - "Community 63"
Cohesion: 0.33
Nodes (5): Извлечение полей программы, Обязательные значения, которые не извлекаются из текста, а проставляются всегда, Поля, которые нужно извлечь, Правила, Текст страницы

### Community 64 - "Community 64"
Cohesion: 0.33
Nodes (5): Виды наблюдений (kind) и что для каждого обязательно заполнить, Наблюдатель чата подготовки, Правила разбора (обязательны для каждого наблюдения), Формат ответа, Что подано на вход

### Community 65 - "Community 65"
Cohesion: 0.33
Nodes (5): Ассистент подбора программ, Жёсткие ограничения, После изменений, Типы реплик — короче, Ход разговора

### Community 66 - "Community 66"
Cohesion: 0.33
Nodes (6): 9.1 Два уровня, 9.2 Слоты контекста топика, 9.3 Формат инъекции, 9.4 Политика поведения, 9.5 Инструменты репетитора (только чтение), 9\. Контекст репетитора

### Community 67 - "Community 67"
Cohesion: 0.60
Nodes (4): Exam date seeding into B1-owned Neo4j Exam nodes., seed_calendars(), TestDate, validate_calendars()

### Community 68 - "Community 68"
Cohesion: 0.40
Nodes (5): 11.1 Честность, 11.2 Главный риск — ложное наблюдение, 11.3 Метрики, 11.4 Отказы, 11\. Честность, качество, отказы

### Community 69 - "Community 69"
Cohesion: 0.40
Nodes (5): 2.1 Канонический слой — общий для всех, ученик не редактирует `[B1]`, 2.2 Персональный слой — на ученика, 2.3 База знаний о поступлении и ExamFormat `[B1 черновик, B2 дополняет]`, 2.4 Индексы и изоляция, 2\. Схема графа (Neo4j)

### Community 70 - "Community 70"
Cohesion: 0.40
Nodes (5): 5.1 Статусы и переходы `MisconceptionState`, 5.2 Видимость, 5.3 Триггеры — при каких условиях проявляется, 5.4 Персональные заблуждения, 5\. Заблуждения

### Community 71 - "Community 71"
Cohesion: 0.50
Nodes (3): on_task_answered(), Event → graph reconciliation (phase 2).  Source: memory-architecture-quack.md, Phase 2: apply task.answered (11 steps of §8.2).      1. Write event → event_i

### Community 72 - "Community 72"
Cohesion: 0.50
Nodes (3): B2 — рабочий журнал, фаза 1, Временные обходы, Что осталось до приёмки §7

## Knowledge Gaps
- **235 isolated node(s):** `WorkerInteractive`, `WorkerBulk`, `quack-api`, `Локальный запуск`, `Текст страницы` (+230 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LLMMessage` connect `Task Templates & Sympy Evaluation` to `Community 41`, `Community 23`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `KnowledgeParams` connect `Community 34` to `Community 41`, `Community 52`, `Community 31`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **What connects `Alembic environment using the application async PostgreSQL settings.`, `app.__init__ skeleton.`, `Agent-facing code: prompts, tool registries, per-chat-kind logic (§5, 30-B2.md).` to the rest of the system?**
  _442 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Learner Knowledge & Misconception State` be split into smaller, more focused modules?**
  _Cohesion score 0.12105263157894737 - nodes in this community are weakly interconnected._
- **Should `Task Templates & Sympy Evaluation` be split into smaller, more focused modules?**
  _Cohesion score 0.058435255290234904 - nodes in this community are weakly interconnected._
- **Should `Community 23` be split into smaller, more focused modules?**
  _Cohesion score 0.11689070718877849 - nodes in this community are weakly interconnected._
- **Should `Community 24` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._