# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 88 files · ~90,565 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 22 file(s) not represented in the graph (top: .css 20, (none) 2)

## Summary
- 691 nodes · 1623 edges · 36 communities (31 shown, 5 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b9709411`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- dashboardRules.ts
- ChoiceApp.tsx
- localSource.ts
- ProgramUi.tsx
- compilerOptions
- react
- What You Must Do When Invoked
- HeroLandscape.tsx
- app/page.tsx
- Globe.tsx
- PixelDuck.tsx
- Quack! — frontend
- prepModel.ts
- standing.ts
- SkillGraph.tsx
- CalendarTab.tsx
- SetsView.tsx
- Icon.tsx
- prepAssistant.ts
- PageSky.tsx
- prepData.ts
- graphify reference: extra exports and benchmark
- package.json
- programs.ts
- Sidebar.tsx
- graphify reference: query, path, explain
- FooterDucks.tsx
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- .claude/CLAUDE.md
- extraction-spec.md
- copy.ts

## God Nodes (most connected - your core abstractions)
1. `react` - 42 edges
2. `ChoiceApp()` - 28 edges
3. `formatDate()` - 23 edges
4. `daysBetween()` - 23 edges
5. `programById()` - 19 edges
6. `computeStanding()` - 19 edges
7. `Icon()` - 16 edges
8. `evaluate()` - 16 edges
9. `compilerOptions` - 16 edges
10. `formatShort()` - 15 edges

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

## Communities (36 total, 5 thin omitted)

### Community 0 - "dashboardRules.ts"
Cohesion: 0.13
Nodes (27): ActivityGrid(), Dashboard(), src_components_dashboard_dashboard_module, Props, activityByDay(), ActivityDay, calendar(), calendarEvents() (+19 more)

### Community 1 - "ChoiceApp.tsx"
Cohesion: 0.05
Nodes (68): react-dom, acknowledge(), CONFIRM_REPLY, editField(), EMPTY_PROFILE, extract(), FieldKey, FIELDS (+60 more)

### Community 2 - "localSource.ts"
Cohesion: 0.07
Nodes (41): ChancesCard(), examWord(), Props, ago(), ChangesFeed(), Props, Target, TARGET_LABEL (+33 more)

### Community 3 - "ProgramUi.tsx"
Cohesion: 0.18
Nodes (16): budgetOf(), evaluate(), formatEur(), Level, LEVEL_LABEL, LevelBadge(), LevelDot(), ProgramActions (+8 more)

### Community 4 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 5 - "react"
Cohesion: 0.19
Nodes (15): react, ChatDemo(), src_components_home_quack_module, QuackSection(), TABS, src_components_home_reveal_module, Reveal(), RevealProps (+7 more)

### Community 6 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 7 - "HeroLandscape.tsx"
Cohesion: 0.12
Nodes (20): Prop(), FLAG_A, FLAG_B, GROUND, HALL, HeroLandscape(), mirror(), PACE (+12 more)

### Community 8 - "app/page.tsx"
Cohesion: 0.11
Nodes (19): metadata, src_components_home_aura_module, copy, CursorAura(), RADIUS, HeroTitle(), measurePath(), Point (+11 more)

### Community 9 - "Globe.tsx"
Cohesion: 0.14
Nodes (21): PROGRAMS, arcDeg(), decodeWorld(), frameCountry(), Globe(), GlobeProps, Land, src_components_home_globe_module (+13 more)

### Community 10 - "PixelDuck.tsx"
Cohesion: 0.09
Nodes (21): src_components_duck_pixel_duck_module, BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels() (+13 more)

### Community 11 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "prepModel.ts"
Cohesion: 0.15
Nodes (26): ChatLine, CheckCanvas(), CurrentSet(), Props, Now(), src_components_prep_prep_module, Evidence, ExamId (+18 more)

### Community 13 - "standing.ts"
Cohesion: 0.19
Nodes (24): hardConflicts(), Important(), Milestones(), Requirements(), daysBetween(), formatDate(), SETS, StudySet (+16 more)

### Community 14 - "SkillGraph.tsx"
Cohesion: 0.09
Nodes (34): Beacon, Beacons(), clamp(), Drag, dropSelection(), GraphCanvas(), Popover, PopoverCard() (+26 more)

### Community 15 - "CalendarTab.tsx"
Cohesion: 0.24
Nodes (14): downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp(), CalendarTab() (+6 more)

### Community 16 - "SetsView.tsx"
Cohesion: 0.18
Nodes (17): useVertical(), forecastSeries(), SET_STATUS_LABEL, disputeMisconception(), MISCONCEPTION_LABEL(), setStatus(), clampGap(), columnScale() (+9 more)

### Community 17 - "Icon.tsx"
Cohesion: 0.15
Nodes (15): Icon(), IconName, Mode, LETTERS, MENU_LABEL, MODES, Topbar(), TopbarProps (+7 more)

### Community 18 - "prepAssistant.ts"
Cohesion: 0.32
Nodes (13): AssistantChat(), addDays(), ASSISTANT_PROMPTS, assistantReply(), examOf(), findDeadline(), minutesPerDay(), openSkills() (+5 more)

### Community 19 - "PageSky.tsx"
Cohesion: 0.18
Nodes (9): Cloud, CLOUD_A, CLOUD_B, CLOUDS, PageSky(), PALETTE, Pass, WEDGE (+1 more)

### Community 20 - "prepData.ts"
Cohesion: 0.09
Nodes (32): ForecastChart(), PAD, Props, useWidth(), Overview(), Programs(), Props, CHECKS (+24 more)

### Community 21 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 22 - "package.json"
Cohesion: 0.05
Nodes (36): nextConfig, dependencies, next, react, react-dom, devDependencies, @types/node, @types/react (+28 more)

### Community 23 - "programs.ts"
Cohesion: 0.27
Nodes (10): CompareView(), CompareViewProps, CompareRow, compareRows(), compareSummary(), Evaluation, Factor, FactorStatus (+2 more)

### Community 24 - "Sidebar.tsx"
Cohesion: 0.20
Nodes (11): ChatSummary, Sidebar(), SidebarProps, SidebarTab, TABS, timeLabel(), DASH_TABS, DashTab (+3 more)

### Community 25 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 26 - "FooterDucks.tsx"
Cohesion: 0.22
Nodes (8): ref_next_link, src_components_home_footer_module, FooterDucks(), POND, TUFT, SCENE_PALETTE, SiteFooter(), TransitionLinkProps

### Community 27 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 28 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 29 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 35 - "copy.ts"
Cohesion: 0.28
Nodes (5): Tempo, ChatDemoProps, ChatThreadProps, ChatTurn, DIALOGUES

## Knowledge Gaps
- **233 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+228 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 279 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `react` to `dashboardRules.ts`, `ChoiceApp.tsx`, `localSource.ts`, `ProgramUi.tsx`, `HeroLandscape.tsx`, `app/page.tsx`, `Globe.tsx`, `PixelDuck.tsx`, `prepModel.ts`, `SkillGraph.tsx`, `CalendarTab.tsx`, `SetsView.tsx`, `Icon.tsx`, `PageSky.tsx`, `prepData.ts`, `package.json`, `Sidebar.tsx`, `FooterDucks.tsx`, `copy.ts`?**
  _High betweenness centrality (0.326) - this node is a cross-community bridge._
- **Why does `ChoiceApp()` connect `ChoiceApp.tsx` to `localSource.ts`, `package.json`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `quackSource` connect `localSource.ts` to `prepModel.ts`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `programById()` (e.g. with `compareRows()` and `Dashboard()`) actually correct?**
  _`programById()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _233 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `dashboardRules.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.12903225806451613 - nodes in this community are weakly interconnected._
- **Should `ChoiceApp.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.05 - nodes in this community are weakly interconnected._