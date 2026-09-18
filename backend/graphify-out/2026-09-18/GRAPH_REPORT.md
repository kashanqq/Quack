# Graph Report - backend  (2026-09-17)

## Corpus Check
- Corpus is ~17,241 words - fits in a single context window. You may not need a graph.

## Summary
- 105 nodes · 122 edges · 23 communities (9 shown, 14 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- API Orchestration & Tool Registry
- Learner Knowledge & Misconception State
- Profile & Evidence-Based Claims
- Chat, LLM & Streaming Infra
- Six-Layer Architecture & Deterministic Rules
- Skill/Misconception Graph & Sets
- Recommendations & Student Autonomy
- Task Templates & Sympy Evaluation
- Canonical Skill Mapping
- Exam Calendars
- Program Cache
- Thesis: Events as Source of Truth
- Thesis: Tutor vs Observer
- Program Comparison
- Exam Format
- Overview Tab
- Program Entity
- Program Web Search Cache
- FastAPI Backend
- Next.js Frontend (tech-stack ref)
- Redis
- Tavily Search
- VPS Deploy

## God Nodes (most connected - your core abstractions)
1. `apps/api структура модулей (knowledge/, tasks/, sets/, matching/, llm/, agents/, workers/, api/)` - 12 edges
2. `L2 Оркестрация / API` - 11 edges
3. `Evidence (свидетельство)` - 9 edges
4. `ИИ-слой (backend README)` - 8 edges
5. `Данные (backend README слой)` - 6 edges
6. `KnowledgeState` - 6 edges
7. `L3 ИИ / языковая модель` - 5 edges
8. `L4 Детерминированные правила` - 5 edges
9. `L5 Данные и хранилище` - 5 edges
10. `get_exam_format` - 5 edges

## Surprising Connections (you probably didn't know these)
- `API / Оркестрация (backend)` --conceptually_related_to--> `Профиль`  [INFERRED]
  README.md → ssot/product-logic.md
- `API / Оркестрация (backend)` --references--> `L2 Оркестрация / API`  [EXTRACTED]
  README.md → ssot/arch-logic.md
- `ИИ-слой (backend README)` --references--> `get_skill_state`  [EXTRACTED]
  README.md → ssot/arch-logic.md
- `ИИ-слой (backend README)` --references--> `L3 ИИ / языковая модель`  [EXTRACTED]
  README.md → ssot/arch-logic.md
- `Детерминированные правила (backend README)` --references--> `L4 Детерминированные правила`  [EXTRACTED]
  README.md → ssot/arch-logic.md

## Hyperedges (group relationships)
- **Шесть слоёв архитектуры Quack (L1–L6)** — backend_ssot_arch_logic_l1_client, backend_ssot_arch_logic_l2_orchestration, backend_ssot_arch_logic_l3_ai_layer, backend_ssot_arch_logic_l4_deterministic_rules, backend_ssot_arch_logic_l5_data_storage, backend_ssot_arch_logic_l6_external_sources [EXTRACTED 1.00]
- **Инструменты, доступные языковой модели (L2)** — backend_ssot_arch_logic_get_exam_format, backend_ssot_arch_logic_get_admission_route, backend_ssot_arch_logic_get_program_requirements, backend_ssot_arch_logic_save_profile_field, backend_ssot_arch_logic_run_program_search, backend_ssot_arch_logic_save_program, backend_ssot_arch_logic_get_skill_state [EXTRACTED 1.00]
- **Конвейер доверия к свидетельствам (ярусы → Evidence → KnowledgeState через HLR)** — backend_ssot_memory_architecture_quack_trust_tiers, backend_ssot_memory_architecture_quack_evidence, backend_ssot_memory_architecture_quack_knowledgestate, backend_ssot_memory_architecture_quack_half_life_regression [INFERRED 0.85]

## Communities (23 total, 14 thin omitted)

### Community 0 - "API Orchestration & Tool Registry"
Cohesion: 0.18
Nodes (19): ИИ-слой (backend README), API / Оркестрация (backend), get_admission_route, get_exam_format, get_program_requirements, get_skill_state, L1 Клиент, L2 Оркестрация / API (+11 more)

### Community 1 - "Learner Knowledge & Misconception State"
Cohesion: 0.16
Nodes (16): Модель знаний ученика, Конфиг (§12, все параметры), Evidence (свидетельство), explain_belief(node_id), get_learner_context(...), Half-life regression (модель забывания), KnowledgeState, Контекст репетитора (<learner_model>, §9) (+8 more)

### Community 2 - "Profile & Evidence-Based Claims"
Cohesion: 0.15
Nodes (13): Данные (backend README слой), frontend localStorage, Граф знаний о поступлении, Датасет задач (arch-logic), Ничего без доказательства (memory-architecture), Свидетельство (product-logic), Веха, Ничего без доказательства (+5 more)

### Community 3 - "Chat, LLM & Streaming Infra"
Cohesion: 0.17
Nodes (12): frontend assistant.ts, Лог событий (events, Postgres), Наблюдатель (чата подготовки), Replay (пересборка графа из событий), Чат подбора (§3.2), Чат подготовки (§4.5), ARQ (фоновые задачи, 2 очереди), LLM-провайдер (OpenAI-совместимый API) (+4 more)

### Community 4 - "Six-Layer Architecture & Deterministic Rules"
Cohesion: 0.23
Nodes (12): Детерминированные правила (backend README), frontend programs.ts, Деградация по слоям (§6.3): таймаут, предгенерация, статус «недоступно», L3 ИИ / языковая модель, L4 Детерминированные правила, L5 Данные и хранилище, L6 Внешние источники, Реактивность: «изменил → изменилось» (§02) (+4 more)

### Community 5 - "Skill/Misconception Graph & Sets"
Cohesion: 0.29
Nodes (7): Misconception (граф-узел, библиотечный+персональный), Skill (граф-узел, канонический+персональный), Текущий сет (§4.4), Первичный замер (§4.2), Заблуждение (product-logic), Навык (product-logic), Neo4j 5 Community

### Community 6 - "Recommendations & Student Autonomy"
Cohesion: 0.40
Nodes (5): Никакой лишней дисциплины, Рекомендации / Quack-лента (§3.6), Маршрут, Сет, Система рекомендует, ученик решает

### Community 7 - "Task Templates & Sympy Evaluation"
Cohesion: 0.50
Nodes (4): Экземпляр задачи (TaskInstance, §3.3), Шаблон задачи (TaskTemplate, §3.1), Задачи и моки — датасет (§5.4), sympy-вычисление шаблонов (§3.4)

### Community 8 - "Canonical Skill Mapping"
Cohesion: 0.67
Nodes (3): Каноническая карта навыков, Персональные узлы навыков, Карта навыков: канонический и персональный слои (§5.2)

## Knowledge Gaps
- **34 isolated node(s):** `Детерминированные правила (backend README)`, `frontend assistant.ts`, `frontend programs.ts`, `frontend localStorage`, `L1 Клиент` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 42 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Evidence (свидетельство)` connect `Learner Knowledge & Misconception State` to `Profile & Evidence-Based Claims`, `Chat, LLM & Streaming Infra`, `Task Templates & Sympy Evaluation`?**
  _High betweenness centrality (0.270) - this node is a cross-community bridge._
- **Why does `apps/api структура модулей (knowledge/, tasks/, sets/, matching/, llm/, agents/, workers/, api/)` connect `API Orchestration & Tool Registry` to `Learner Knowledge & Misconception State`, `Six-Layer Architecture & Deterministic Rules`, `Recommendations & Student Autonomy`?**
  _High betweenness centrality (0.224) - this node is a cross-community bridge._
- **Why does `KnowledgeState` connect `Learner Knowledge & Misconception State` to `Skill/Misconception Graph & Sets`?**
  _High betweenness centrality (0.208) - this node is a cross-community bridge._
- **What connects `Детерминированные правила (backend README)`, `frontend assistant.ts`, `frontend programs.ts` to the rest of the system?**
  _34 weakly-connected nodes found - possible documentation gaps or missing edges._