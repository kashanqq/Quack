# Graph Report - frontend  (2026-09-19)

## Corpus Check
- 100 files · ~119,280 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 27 file(s) not represented in the graph (top: .css 23, (none) 2, .example 1)

## Summary
- 891 nodes · 2008 edges · 53 communities (45 shown, 8 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3f8a2bee`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- programs.ts
- journeyArt.ts
- assistant.ts
- JourneySection.tsx
- compilerOptions
- src_components_home_quack_module
- TopicWorkspace.tsx
- next
- UserMenu.tsx
- Globe.tsx
- PixelDuck.tsx
- Quack! — frontend
- SkillGraph.tsx
- prepData.ts
- dashboardRules.ts
- What You Must Do When Invoked
- Sidebar.tsx
- package.json
- Overview.tsx
- prepModel.ts
- SetsView.tsx
- GraphCanvas.tsx
- AuthGate.tsx
- layout.tsx
- JourneySection
- glintMap
- app/page.tsx
- SetDetail.tsx
- store.ts
- AuthApi
- graphify reference: extra exports and benchmark
- localAuth.ts
- FooterDucks.tsx
- prepAssistant.ts
- graphify reference: query, path, explain
- schema.d.ts
- PageSky.tsx
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- standing.ts
- react
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- .claude/CLAUDE.md
- HeroLandscape.tsx
- extraction-spec.md
- StateBackend
- Closing.tsx
- CalendarTab.tsx
- LoginView.tsx
- ChoiceApp.tsx

## God Nodes (most connected - your core abstractions)
1. `react` - 47 edges
2. `ChoiceApp()` - 27 edges
3. `daysBetween()` - 26 edges
4. `formatDate()` - 24 edges
5. `formatShort()` - 22 edges
6. `skillById()` - 20 edges
7. `programById()` - 19 edges
8. `computeStanding()` - 19 edges
9. `Icon()` - 17 edges
10. `evaluate()` - 16 edges

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

## Communities (53 total, 8 thin omitted)

### Community 0 - "programs.ts"
Cohesion: 0.12
Nodes (29): Profile, CompareView(), CompareViewProps, budgetOf(), CompareRow, compareRows(), compareSummary(), evaluate() (+21 more)

### Community 1 - "journeyArt.ts"
Cohesion: 0.08
Nodes (23): ARCH, BOAT, BUSH, FOG_PALETTE, FOG_PROPS, fogIsle(), GULL, HUT (+15 more)

### Community 2 - "assistant.ts"
Cohesion: 0.07
Nodes (44): acknowledge(), editField(), extract(), FieldKey, FIELDS, FieldStatus, fieldValue(), labelOf() (+36 more)

### Community 3 - "JourneySection.tsx"
Cohesion: 0.06
Nodes (28): src_components_home_journey_module, bezier(), Box, FOG, Ghost, HALF, ISLE_1, ISLE_1_SIZE (+20 more)

### Community 4 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 6 - "TopicWorkspace.tsx"
Cohesion: 0.09
Nodes (38): downloadMarkdown(), escape(), generateCards(), generateNotes(), inline(), markdownToHtml(), materialAsked(), MaterialKind (+30 more)

### Community 7 - "next"
Cohesion: 0.20
Nodes (5): nextConfig, next, metadata, LoginView(), safeNext()

### Community 8 - "UserMenu.tsx"
Cohesion: 0.17
Nodes (13): ref_next_navigation, useAccount(), Props, UserMenu(), DEMO_SHIFT, shiftDemoClock(), src_components_transition_transition_module, TransitionLink() (+5 more)

### Community 9 - "Globe.tsx"
Cohesion: 0.14
Nodes (21): PROGRAMS, arcDeg(), decodeWorld(), frameCountry(), Globe(), GlobeProps, Land, src_components_home_globe_module (+13 more)

### Community 10 - "PixelDuck.tsx"
Cohesion: 0.14
Nodes (15): src_components_duck_pixel_duck_module, BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels() (+7 more)

### Community 11 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "SkillGraph.tsx"
Cohesion: 0.12
Nodes (22): AREAS, EXAM_IDS, Misconception, Skill, SKILLS, SkillState, along(), autoLayout() (+14 more)

### Community 13 - "prepData.ts"
Cohesion: 0.09
Nodes (23): ForecastChart(), PAD, Props, useWidth(), src_components_prep_prep_module, conflicts(), DEMO_SAVED, Evidence (+15 more)

### Community 14 - "dashboardRules.ts"
Cohesion: 0.14
Nodes (27): ActivityGrid(), Dashboard(), src_components_dashboard_dashboard_module, Props, activityByDay(), ActivityDay, calendar(), calendarEvents() (+19 more)

### Community 15 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 16 - "Sidebar.tsx"
Cohesion: 0.10
Nodes (23): Icon(), IconName, ChatSummary, Mode, Sidebar(), SidebarProps, SidebarTab, TABS (+15 more)

### Community 17 - "package.json"
Cohesion: 0.07
Nodes (25): dependencies, next, react, react-dom, devDependencies, openapi-typescript, @types/node, @types/react (+17 more)

### Community 18 - "Overview.tsx"
Cohesion: 0.23
Nodes (16): Important(), Now(), Overview(), Props, Requirements(), day(), daysBetween(), forecastSeries() (+8 more)

### Community 19 - "prepModel.ts"
Cohesion: 0.18
Nodes (18): ExamId, savedPrograms(), acceptSet(), AnswerResult, GAP, initialModel(), makeCurrent(), PrepSub (+10 more)

### Community 20 - "SetsView.tsx"
Cohesion: 0.17
Nodes (19): formatShort(), SETS, disputeMisconception(), rankSets(), setStatus(), clampGap(), columnScale(), isNow() (+11 more)

### Community 21 - "GraphCanvas.tsx"
Cohesion: 0.22
Nodes (12): Beacon, Beacons(), clamp(), Drag, dropSelection(), GraphCanvas(), Popover, PopoverCard() (+4 more)

### Community 22 - "AuthGate.tsx"
Cohesion: 0.24
Nodes (6): metadata, src_components_account_account_module, Account, AccountContext, AuthGate(), ChoiceRoot()

### Community 23 - "layout.tsx"
Cohesion: 0.22
Nodes (7): ref_next_font_google, src_app_globals, intelOneMono, inter, metadata, raleway, ScrollToTopOnReload()

### Community 24 - "JourneySection"
Cohesion: 0.18
Nodes (13): signalArc(), boatDistance(), clamp01(), JourneySection(), lerp(), place(), pointAt(), routeAt() (+5 more)

### Community 25 - "glintMap"
Cohesion: 0.32
Nodes (8): glintMap(), islandSlice(), islandTop(), noise(), radius(), IslandBody(), Water(), usePoolImage()

### Community 26 - "app/page.tsx"
Cohesion: 0.12
Nodes (18): ref_next_link, metadata, src_components_home_aura_module, copy, CursorAura(), RADIUS, src_components_home_layers_module, LayerStack() (+10 more)

### Community 27 - "SetDetail.tsx"
Cohesion: 0.15
Nodes (16): useVertical(), EXAMS, SET_STATUS_LABEL, STATE_LABEL, PrepModel, Due, DUE_TEXT, dueOf() (+8 more)

### Community 28 - "store.ts"
Cohesion: 0.24
Nodes (10): adoptLegacy(), cache, DEVICE, flush(), flushOnExit(), localBackend, pending, prefix() (+2 more)

### Community 30 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 31 - "localAuth.ts"
Cohesion: 0.28
Nodes (5): Account, derive(), publicPart(), startSession(), toHex()

### Community 32 - "FooterDucks.tsx"
Cohesion: 0.38
Nodes (5): src_components_home_footer_module, FooterDucks(), POND, TUFT, SCENE_PALETTE

### Community 33 - "prepAssistant.ts"
Cohesion: 0.35
Nodes (13): PaceCard(), addDays(), ASSISTANT_PROMPTS, assistantReply(), examOf(), findDeadline(), minutesPerDay(), openSkills() (+5 more)

### Community 34 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 35 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 36 - "PageSky.tsx"
Cohesion: 0.12
Nodes (16): Cloud, CLOUD_A, CLOUD_B, CLOUDS, PageSky(), PALETTE, Pass, WEDGE (+8 more)

### Community 37 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 38 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 39 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 40 - "standing.ts"
Cohesion: 0.07
Nodes (49): ChancesCard(), examWord(), Props, Conflict, EXAMS, setById(), ChanceFact, EMPTY_STATE (+41 more)

### Community 41 - "react"
Cohesion: 0.12
Nodes (17): react, src_components_home_duck_lane_module, BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight (+9 more)

### Community 46 - "HeroLandscape.tsx"
Cohesion: 0.13
Nodes (17): Prop(), FLAG_A, FLAG_B, GROUND, HALL, HeroLandscape(), mirror(), PACE (+9 more)

### Community 49 - "Closing.tsx"
Cohesion: 0.15
Nodes (11): ANGLER, Closing(), FLOAT, GROUND_WIDE, LAKE, src_components_home_closing_module, PALETTE, ROD_BENT (+3 more)

### Community 50 - "CalendarTab.tsx"
Cohesion: 0.24
Nodes (14): downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp(), CalendarTab() (+6 more)

### Community 55 - "LoginView.tsx"
Cohesion: 0.18
Nodes (13): auth, AuthError, AuthErrorCode, EMAIL_RE, PASSWORD_MIN, User, localAuth, ERRORS (+5 more)

### Community 58 - "ChoiceApp.tsx"
Cohesion: 0.11
Nodes (19): store, CONFIRM_REPLY, EMPTY_PROFILE, ChatMessage(), ChatMessageProps, ChatMsg, ChatItem, GREETINGS (+11 more)

## Knowledge Gaps
- **298 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+293 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 371 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `react` to `programs.ts`, `assistant.ts`, `JourneySection.tsx`, `TopicWorkspace.tsx`, `next`, `UserMenu.tsx`, `Globe.tsx`, `PixelDuck.tsx`, `SkillGraph.tsx`, `prepData.ts`, `dashboardRules.ts`, `Sidebar.tsx`, `package.json`, `prepModel.ts`, `SetsView.tsx`, `GraphCanvas.tsx`, `AuthGate.tsx`, `layout.tsx`, `JourneySection`, `app/page.tsx`, `SetDetail.tsx`, `FooterDucks.tsx`, `PageSky.tsx`, `standing.ts`, `HeroLandscape.tsx`, `Closing.tsx`, `CalendarTab.tsx`, `LoginView.tsx`, `ChoiceApp.tsx`?**
  _High betweenness centrality (0.374) - this node is a cross-community bridge._
- **Why does `ChoiceApp()` connect `assistant.ts` to `programs.ts`, `standing.ts`, `prepModel.ts`, `AuthGate.tsx`, `ChoiceApp.tsx`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `PixelDuck()` connect `PixelDuck.tsx` to `FooterDucks.tsx`, `assistant.ts`, `JourneySection.tsx`, `PageSky.tsx`, `UserMenu.tsx`, `react`, `HeroLandscape.tsx`, `Sidebar.tsx`, `Closing.tsx`, `AuthGate.tsx`, `LoginView.tsx`, `ChoiceApp.tsx`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _298 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `programs.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Should `journeyArt.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `assistant.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.07372549019607844 - nodes in this community are weakly interconnected._