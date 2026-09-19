# Graph Report - frontend  (2026-09-19)

## Corpus Check
- 105 files · ~121,648 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 27 file(s) not represented in the graph (top: .css 23, (none) 2, .example 1)

## Summary
- 913 nodes · 2063 edges · 51 communities (43 shown, 8 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d8654e43`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- standing.ts
- journeyArt.ts
- ChoiceApp
- JourneySection.tsx
- compilerOptions
- src_components_home_quack_module
- TopicWorkspace.tsx
- programs.ts
- AuthGate.tsx
- Globe.tsx
- PixelDuck.tsx
- Quack! — frontend
- GraphCanvas.tsx
- prepData.ts
- JourneySection
- What You Must Do When Invoked
- localAuth.ts
- package.json
- prepModel.ts
- RouteView.tsx
- Sidebar.tsx
- PrepView.tsx
- milestoneIntent.ts
- login/page.tsx
- store.ts
- app/page.tsx
- SetDetail.tsx
- LoginView.tsx
- glintMap
- graphify reference: extra exports and benchmark
- remoteAuth.ts
- GlobeSection.tsx
- prepAssistant.ts
- graphify reference: query, path, explain
- schema.d.ts
- react
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- localSource.ts
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- .claude/CLAUDE.md
- Closing.tsx
- extraction-spec.md
- FirstHint.tsx
- AuthApi
- StateBackend
- assistant.ts
- ChoiceApp.tsx

## God Nodes (most connected - your core abstractions)
1. `react` - 49 edges
2. `ChoiceApp()` - 32 edges
3. `daysBetween()` - 28 edges
4. `skillById()` - 22 edges
5. `programById()` - 21 edges
6. `formatShort()` - 20 edges
7. `Icon()` - 19 edges
8. `formatDate()` - 19 edges
9. `computeStanding()` - 18 edges
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

## Communities (51 total, 8 thin omitted)

### Community 0 - "standing.ts"
Cohesion: 0.06
Nodes (76): budgetOf(), Program, ActivityGrid(), downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay() (+68 more)

### Community 1 - "journeyArt.ts"
Cohesion: 0.08
Nodes (23): ARCH, BOAT, BUSH, FOG_PALETTE, FOG_PROPS, fogIsle(), GULL, HUT (+15 more)

### Community 2 - "ChoiceApp"
Cohesion: 0.16
Nodes (22): editField(), placeholderFor(), readiness(), ChoiceApp(), applyToProfile(), assistantSay(), handleIntent(), handleMilestone() (+14 more)

### Community 3 - "JourneySection.tsx"
Cohesion: 0.06
Nodes (28): src_components_home_journey_module, bezier(), Box, FOG, Ghost, HALF, ISLE_1, ISLE_1_SIZE (+20 more)

### Community 4 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 6 - "TopicWorkspace.tsx"
Cohesion: 0.14
Nodes (25): downloadMarkdown(), escape(), generateCards(), generateNotes(), inline(), markdownToHtml(), materialAsked(), MaterialKind (+17 more)

### Community 7 - "programs.ts"
Cohesion: 0.15
Nodes (24): Profile, CompareView(), CompareViewProps, CompareRow, compareRows(), compareSummary(), evaluate(), Evaluation (+16 more)

### Community 8 - "AuthGate.tsx"
Cohesion: 0.11
Nodes (18): ref_next_navigation, metadata, Account, AccountContext, AuthGate(), useAccount(), ChoiceRoot(), Props (+10 more)

### Community 9 - "Globe.tsx"
Cohesion: 0.15
Nodes (20): arcDeg(), decodeWorld(), frameCountry(), Globe(), GlobeProps, Land, src_components_home_globe_module, OPEN_COUNTRIES (+12 more)

### Community 10 - "PixelDuck.tsx"
Cohesion: 0.10
Nodes (21): src_components_duck_pixel_duck_module, BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels() (+13 more)

### Community 11 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "GraphCanvas.tsx"
Cohesion: 0.20
Nodes (13): store, Beacon, Beacons(), clamp(), Drag, dropSelection(), GraphCanvas(), Popover (+5 more)

### Community 13 - "prepData.ts"
Cohesion: 0.08
Nodes (25): ENT_AREAS, ENT_CHECKS, ENT_SETS, ENT_SKILLS, ENT_TOPICS, AREAS, CHECKS, DEMO_SAVED (+17 more)

### Community 14 - "JourneySection"
Cohesion: 0.18
Nodes (13): signalArc(), boatDistance(), clamp01(), JourneySection(), lerp(), place(), pointAt(), routeAt() (+5 more)

### Community 15 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 16 - "localAuth.ts"
Cohesion: 0.24
Nodes (6): User, Account, derive(), publicPart(), startSession(), toHex()

### Community 17 - "package.json"
Cohesion: 0.06
Nodes (31): nextConfig, dependencies, next, react, react-dom, devDependencies, openapi-typescript, @types/node (+23 more)

### Community 18 - "prepModel.ts"
Cohesion: 0.14
Nodes (14): Evidence, Misconception, SetStatus, SKILLS, AnswerResult, answerTask(), GAP, MOCK_SOLID (+6 more)

### Community 19 - "RouteView.tsx"
Cohesion: 0.10
Nodes (28): useVertical(), src_components_prep_prep_module, EXAM_IDS, EXAMS, SkillState, STATE_LABEL, closed(), MAX_PROPOSED (+20 more)

### Community 20 - "Sidebar.tsx"
Cohesion: 0.11
Nodes (22): Icon(), IconName, LevelDot(), ProgramActions, ChatSummary, Mode, Sidebar(), SidebarProps (+14 more)

### Community 21 - "PrepView.tsx"
Cohesion: 0.11
Nodes (25): react-dom, undoMilestone(), DIAGNOSTIC_8_QUESTIONS, DiagnosticQuestion, DiagnosticResultSummary, evaluateDiagnostic(), DiagnosticMock(), Props (+17 more)

### Community 22 - "milestoneIntent.ts"
Cohesion: 0.27
Nodes (10): ALIASES, examIn(), milestoneIntent, programIn(), word(), PROGRAMS, day(), milestones() (+2 more)

### Community 23 - "login/page.tsx"
Cohesion: 0.29
Nodes (3): metadata, LoginView(), safeNext()

### Community 24 - "store.ts"
Cohesion: 0.24
Nodes (10): adoptLegacy(), cache, DEVICE, flush(), flushOnExit(), localBackend, pending, prefix() (+2 more)

### Community 26 - "app/page.tsx"
Cohesion: 0.10
Nodes (25): ref_next_link, metadata, src_components_home_aura_module, Closing(), copy, CursorAura(), RADIUS, src_components_home_footer_module (+17 more)

### Community 27 - "SetDetail.tsx"
Cohesion: 0.21
Nodes (12): SET_STATUS_LABEL, PrepModel, setStatus(), Due, DUE_TEXT, dueOf(), plannedDates(), Props (+4 more)

### Community 28 - "LoginView.tsx"
Cohesion: 0.24
Nodes (9): src_components_account_account_module, auth, AuthErrorCode, EMAIL_RE, PASSWORD_MIN, localAuth, ERRORS, Mode (+1 more)

### Community 29 - "glintMap"
Cohesion: 0.32
Nodes (8): glintMap(), islandSlice(), islandTop(), noise(), radius(), IslandBody(), Water(), usePoolImage()

### Community 30 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 31 - "remoteAuth.ts"
Cohesion: 0.38
Nodes (4): AuthError, call(), fail(), StudentCtx

### Community 32 - "GlobeSection.tsx"
Cohesion: 0.29
Nodes (6): DuckLane(), src_components_home_globe_section_module, GlobeSection(), src_components_home_reveal_module, Reveal(), RevealProps

### Community 33 - "prepAssistant.ts"
Cohesion: 0.33
Nodes (13): addDays(), ASSISTANT_PROMPTS, assistantReply(), examOf(), findDeadline(), minutesPerDay(), openSkills(), plan() (+5 more)

### Community 34 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 35 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 36 - "react"
Cohesion: 0.12
Nodes (17): react, Cloud, CLOUD_A, CLOUD_B, CLOUDS, PageSky(), PALETTE, Pass (+9 more)

### Community 37 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 38 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 39 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 40 - "localSource.ts"
Cohesion: 0.07
Nodes (38): Level, ChancesCard(), examWord(), Props, ago(), ChangesFeed(), Props, Target (+30 more)

### Community 46 - "Closing.tsx"
Cohesion: 0.08
Nodes (30): ANGLER, FLOAT, GROUND_WIDE, LAKE, src_components_home_closing_module, PALETTE, ROD_BENT, ROD_STRAIGHT (+22 more)

### Community 48 - "FirstHint.tsx"
Cohesion: 0.17
Nodes (12): Entry, Help, HelpContext, HelpDialog(), HelpDuck(), HelpProvider(), HelpState, Opened (+4 more)

### Community 53 - "assistant.ts"
Cohesion: 0.11
Nodes (23): acknowledge(), CONFIRM_REPLY, EMPTY_PROFILE, extract(), FieldKey, FIELDS, FieldStatus, fieldValue() (+15 more)

### Community 58 - "ChoiceApp.tsx"
Cohesion: 0.15
Nodes (15): ChatMessage(), ChatMessageProps, ChatMsg, src_components_choice_choice_module, ChatItem, GREETINGS, LeftPanel, RightPanel (+7 more)

## Knowledge Gaps
- **310 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+305 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 389 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `react` to `standing.ts`, `JourneySection.tsx`, `TopicWorkspace.tsx`, `programs.ts`, `AuthGate.tsx`, `Globe.tsx`, `PixelDuck.tsx`, `GraphCanvas.tsx`, `JourneySection`, `package.json`, `RouteView.tsx`, `Sidebar.tsx`, `PrepView.tsx`, `login/page.tsx`, `app/page.tsx`, `SetDetail.tsx`, `LoginView.tsx`, `GlobeSection.tsx`, `localSource.ts`, `Closing.tsx`, `FirstHint.tsx`, `assistant.ts`, `ChoiceApp.tsx`?**
  _High betweenness centrality (0.349) - this node is a cross-community bridge._
- **Why does `PixelDuck()` connect `PixelDuck.tsx` to `standing.ts`, `JourneySection.tsx`, `react`, `AuthGate.tsx`, `Closing.tsx`, `FirstHint.tsx`, `Sidebar.tsx`, `assistant.ts`, `app/page.tsx`, `LoginView.tsx`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `ChoiceApp()` connect `ChoiceApp` to `standing.ts`, `programs.ts`, `AuthGate.tsx`, `PrepView.tsx`, `assistant.ts`, `milestoneIntent.ts`, `ChoiceApp.tsx`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `programById()` (e.g. with `compareRows()` and `Dashboard()`) actually correct?**
  _`programById()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _310 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `standing.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.06138841078600115 - nodes in this community are weakly interconnected._
- **Should `journeyArt.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._