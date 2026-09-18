# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 87 files · ~87,645 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 22 file(s) not represented in the graph (top: .css 20, (none) 2)

## Summary
- 667 nodes · 1544 edges · 35 communities (30 shown, 5 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `096ae56e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- standing.ts
- ChoiceApp.tsx
- localSource.ts
- Sidebar.tsx
- compilerOptions
- QuackSection.tsx
- What You Must Do When Invoked
- HeroLandscape.tsx
- app/page.tsx
- Globe.tsx
- DuckLane.tsx
- Quack! — frontend
- CurrentSet.tsx
- prepData.ts
- SkillGraph.tsx
- GraphCanvas.tsx
- SetsView.tsx
- react
- PixelDuck.tsx
- PageSky.tsx
- Overview.tsx
- graphify reference: extra exports and benchmark
- package.json
- PrepView.tsx
- ForecastChart.tsx
- graphify reference: query, path, explain
- Roadmap.tsx
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- .claude/CLAUDE.md
- extraction-spec.md

## God Nodes (most connected - your core abstractions)
1. `react` - 41 edges
2. `ChoiceApp()` - 28 edges
3. `formatDate()` - 20 edges
4. `daysBetween()` - 20 edges
5. `programById()` - 19 edges
6. `computeStanding()` - 19 edges
7. `Icon()` - 16 edges
8. `evaluate()` - 16 edges
9. `compilerOptions` - 16 edges
10. `Dashboard()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Dashboard()` --indirect_call--> `programById()`  [INFERRED]
  src/components/dashboard/Dashboard.tsx → src/components/choice/programs.ts
- `savedPrograms()` --indirect_call--> `programById()`  [INFERRED]
  src/components/prep/prepData.ts → src/components/choice/programs.ts
- `describePrep()` --indirect_call--> `programById()`  [INFERRED]
  src/components/quack/localSource.ts → src/components/choice/programs.ts
- `computeStanding()` --indirect_call--> `programById()`  [INFERRED]
  src/components/quack/standing.ts → src/components/choice/programs.ts
- `Requirements()` --indirect_call--> `formatShort()`  [INFERRED]
  src/components/prep/Overview.tsx → src/components/prep/prepData.ts

## Import Cycles
- None detected.

## Communities (35 total, 5 thin omitted)

### Community 0 - "standing.ts"
Cohesion: 0.06
Nodes (72): budgetOf(), ActivityGrid(), downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad() (+64 more)

### Community 1 - "ChoiceApp.tsx"
Cohesion: 0.06
Nodes (57): acknowledge(), CONFIRM_REPLY, editField(), EMPTY_PROFILE, extract(), FieldKey, FieldStatus, fieldValue() (+49 more)

### Community 2 - "localSource.ts"
Cohesion: 0.07
Nodes (39): FIELDS, ChancesCard(), examWord(), Props, ago(), ChangesFeed(), Props, Target (+31 more)

### Community 3 - "Sidebar.tsx"
Cohesion: 0.09
Nodes (42): Profile, CompareView(), CompareViewProps, Icon(), IconName, src_components_choice_layout_module, CompareRow, compareRows() (+34 more)

### Community 4 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 5 - "QuackSection.tsx"
Cohesion: 0.12
Nodes (22): Program, PROGRAMS, Tempo, ChatDemo(), ChatDemoProps, ChatThreadProps, ChatTurn, copy (+14 more)

### Community 6 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 7 - "HeroLandscape.tsx"
Cohesion: 0.10
Nodes (20): ref_next_link, src_components_home_footer_module, FooterDucks(), POND, TUFT, FLAG_A, FLAG_B, GROUND (+12 more)

### Community 8 - "app/page.tsx"
Cohesion: 0.15
Nodes (13): metadata, src_components_home_aura_module, CursorAura(), RADIUS, HeroTitle(), measurePath(), Point, src_components_home_home_module (+5 more)

### Community 9 - "Globe.tsx"
Cohesion: 0.15
Nodes (20): arcDeg(), decodeWorld(), frameCountry(), Globe(), GlobeProps, Land, src_components_home_globe_module, OPEN_COUNTRIES (+12 more)

### Community 10 - "DuckLane.tsx"
Cohesion: 0.12
Nodes (17): src_components_home_duck_lane_module, BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight, PARACHUTE (+9 more)

### Community 11 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "CurrentSet.tsx"
Cohesion: 0.16
Nodes (18): ChatLine, GuideCanvas(), PrepChat(), Props, TaskCanvas(), tutorReply(), Now(), GUIDELINES (+10 more)

### Community 13 - "prepData.ts"
Cohesion: 0.15
Nodes (16): DEMO_SAVED, Evidence, ExamRequirement, Guideline, Milestone, Misconception, MisconceptionStatus, MONTHS (+8 more)

### Community 14 - "SkillGraph.tsx"
Cohesion: 0.14
Nodes (16): AREAS, Skill, along(), autoLayout(), BASE, depthOf(), edgePath(), horizontalLayout() (+8 more)

### Community 15 - "GraphCanvas.tsx"
Cohesion: 0.18
Nodes (16): Beacon, Beacons(), clamp(), Drag, dropSelection(), GraphCanvas(), Popover, PopoverCard() (+8 more)

### Community 16 - "SetsView.tsx"
Cohesion: 0.26
Nodes (16): useVertical(), day(), forecastSeries(), formatShort(), closed(), setStatus(), AllSets(), clampGap() (+8 more)

### Community 17 - "react"
Cohesion: 0.20
Nodes (13): ref_next_navigation, react, Props, UserMenu(), DEMO_SHIFT, shiftDemoClock(), src_components_transition_transition_module, TransitionLink() (+5 more)

### Community 18 - "PixelDuck.tsx"
Cohesion: 0.16
Nodes (12): src_components_duck_pixel_duck_module, BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels() (+4 more)

### Community 19 - "PageSky.tsx"
Cohesion: 0.18
Nodes (9): Cloud, CLOUD_A, CLOUD_B, CLOUDS, PageSky(), PALETTE, Pass, WEDGE (+1 more)

### Community 20 - "Overview.tsx"
Cohesion: 0.25
Nodes (10): Milestones(), Overview(), Programs(), Props, conflicts(), milestones(), realismShift(), requirements() (+2 more)

### Community 21 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 22 - "package.json"
Cohesion: 0.05
Nodes (34): nextConfig, dependencies, next, react, react-dom, devDependencies, @types/node, @types/react (+26 more)

### Community 23 - "PrepView.tsx"
Cohesion: 0.33
Nodes (8): savedPrograms(), acceptSet(), makeCurrent(), PrepModel, PrepView(), Props, SetsView(), morph()

### Community 24 - "ForecastChart.tsx"
Cohesion: 0.29
Nodes (7): ForecastChart(), PAD, Props, useWidth(), src_components_prep_prep_module, ForecastPoint, TODAY

### Community 25 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 26 - "Roadmap.tsx"
Cohesion: 0.40
Nodes (4): src_components_home_roadmap_module, Roadmap(), STEPS, StepState

### Community 27 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 28 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 29 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **228 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+223 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 272 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `react` to `standing.ts`, `ChoiceApp.tsx`, `localSource.ts`, `Sidebar.tsx`, `QuackSection.tsx`, `HeroLandscape.tsx`, `app/page.tsx`, `Globe.tsx`, `DuckLane.tsx`, `CurrentSet.tsx`, `SkillGraph.tsx`, `GraphCanvas.tsx`, `SetsView.tsx`, `PixelDuck.tsx`, `PageSky.tsx`, `package.json`, `PrepView.tsx`, `ForecastChart.tsx`, `Roadmap.tsx`?**
  _High betweenness centrality (0.334) - this node is a cross-community bridge._
- **Why does `ChoiceApp()` connect `ChoiceApp.tsx` to `standing.ts`, `package.json`, `PrepView.tsx`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `quackSource` connect `localSource.ts` to `PrepView.tsx`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `programById()` (e.g. with `compareRows()` and `Dashboard()`) actually correct?**
  _`programById()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _228 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `standing.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.06296656929568321 - nodes in this community are weakly interconnected._
- **Should `ChoiceApp.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.06151062867480778 - nodes in this community are weakly interconnected._