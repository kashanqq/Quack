# Graph Report - Lupidrupi  (2026-09-17)

## Corpus Check
- 39 files · ~43,959 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 244 nodes · 291 edges · 25 communities (18 shown, 7 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 16 edges
2. `What You Must Do When Invoked` - 12 edges
3. `/graphify` - 11 edges
4. `respond()` - 8 edges
5. `graphify reference: extra exports and benchmark` - 8 edges
6. `4\. Раздел «Подготовка»` - 8 edges
7. `assistantSay()` - 7 edges
8. `3\. Раздел «Подбор»` - 7 edges
9. `**5\. Данные**` - 7 edges
10. `Продуктовая логика — \[Quack\!\]` - 6 edges

## Surprising Connections (you probably didn't know these)
- `assistantSay()` --calls--> `sleep()`  [INFERRED]
  site/choice.js → src/components/choice/ChoiceApp.tsx
- `flyDuck()` --calls--> `rand()`  [INFERRED]
  site/common.js → src/components/duck/FlyingDucks.tsx
- `ChoiceApp()` --calls--> `readiness()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts
- `Topbar()` --calls--> `usePageTransition()`  [EXTRACTED]
  src/components/choice/Topbar.tsx → src/components/transition/TransitionProvider.tsx
- `TransitionLink()` --calls--> `usePageTransition()`  [EXTRACTED]
  src/components/transition/TransitionLink.tsx → src/components/transition/TransitionProvider.tsx

## Import Cycles
- None detected.

## Communities (25 total, 7 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (27): acknowledge(), EMPTY_PROFILE, extract(), FieldKey, FIELDS, fieldValue(), MissingKey, nextMissing() (+19 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (19): intelOneMono, inter, khula, metadata, montserratAlternates, raleway, Topbar(), Duck() (+11 more)

### Community 2 - "Community 2"
Cohesion: 0.17
Nodes (20): sleep(), acknowledge(), addMessage(), addSummaryActions(), assistantSay(), cancelEdit(), confirmSummary(), ensureConfirmButton() (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 4 - "Community 4"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (15): Part A - Structural extraction for code files, Part B - Semantic extraction (parallel subagents), Part C - Merge AST + semantic into final extraction, Step 0 - GitHub repos and multi-path merge (only if a URL or several paths), Step 1 - Ensure graphify is installed, Step 2.5 - Video and audio (only if video files detected), Step 2 - Detect files, Step 3 - Extract entities and relationships (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (14): 4.1 Обзор, 4.2 Первичный замер, 4.3 Сеты, 4.4 Текущий сет, 4.5 Чат подготовки, 4.6 Рекомендации в подготовке, 4\. Раздел «Подготовка», **5.0 База знаний о поступлении (GraphRAG)** (+6 more)

### Community 7 - "Community 7"
Cohesion: 0.17
Nodes (11): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, PowerShell 5.1: Vertical scrolling stops working (+3 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (11): 0\. Шапка, 1\. Пользователь, 2\. Продукт целиком, 3.1 Профиль, 3.2 Чат подбора, 3.3 Подборка, 3.4 Сравнение\[ДОРАБОТАТЬ\!\], 3.5 Сохраненные (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.20
Nodes (9): 1.1. Проблема, 1.2. Цели (Goals), 1.3. Не-цели (Non-Goals), 1. Обзор и цели (Overview & Goals), 2.1. Цветовая палитра, 2.2. Ключевые экраны, 2. UI/UX & Дизайн-система, 3. Архитектура системы (High-Level Architecture) (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 11 - "Community 11"
Cohesion: 0.32
Nodes (4): Roadmap(), STEPS, StepState, SiteHeader()

### Community 12 - "Community 12"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 14 - "Community 14"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 15 - "Community 15"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 16 - "Community 16"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **124 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+119 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sleep()` connect `Community 2` to `Community 0`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _124 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.1051693404634581 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.10052910052910052 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `Community 5` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._