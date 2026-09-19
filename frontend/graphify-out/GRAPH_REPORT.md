# Graph Report - frontend  (2026-09-19)

## Corpus Check
- 105 files · ~123,368 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 27 file(s) not represented in the graph (top: .css 23, (none) 2, .example 1)

## Summary
- 932 nodes · 2175 edges · 52 communities (45 shown, 7 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.85)
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
- Dashboard.tsx
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
- SetDetail.tsx
- layout.tsx
- milestoneMarks.ts
- DuckLane.tsx
- LoginView.tsx
- store.ts
- fieldValue
- app/page.tsx
- FooterDucks.tsx
- TransitionLink.tsx
- glintMap
- graphify reference: extra exports and benchmark
- remoteAuth.ts
- Closing.tsx
- prepAssistant.ts
- graphify reference: query, path, explain
- schema.d.ts
- PageSky.tsx
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- localSource.ts
- ActivityGrid.tsx
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- .claude/CLAUDE.md
- HeroLandscape.tsx
- extraction-spec.md
- FirstHint.tsx
- AuthApi
- assistant.ts
- ChoiceApp.tsx

## God Nodes (most connected - your core abstractions)
1. `react` - 49 edges
2. `ChoiceApp()` - 39 edges
3. `formatDate()` - 29 edges
4. `daysBetween()` - 28 edges
5. `skillById()` - 22 edges
6. `programById()` - 21 edges
7. `formatShort()` - 20 edges
8. `Icon()` - 19 edges
9. `plannedTest()` - 19 edges
10. `computeStanding()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Dashboard()` --indirect_call--> `programById()`  [INFERRED]
  src/components/dashboard/Dashboard.tsx → src/components/choice/programs.ts
- `savedPrograms()` --indirect_call--> `programById()`  [INFERRED]
  src/components/prep/prepData.ts → src/components/choice/programs.ts
- `describePrep()` --indirect_call--> `programById()`  [INFERRED]
  src/components/quack/localSource.ts → src/components/choice/programs.ts
- `computeStanding()` --indirect_call--> `programById()`  [INFERRED]
  src/components/quack/standing.ts → src/components/choice/programs.ts
- `call()` --calls--> `AuthError`  [EXTRACTED]
  src/components/account/remoteAuth.ts → src/components/account/contract.ts

## Import Cycles
- None detected.

## Communities (52 total, 7 thin omitted)

### Community 0 - "standing.ts"
Cohesion: 0.06
Nodes (85): ALIASES, dateIn(), examIn(), milestoneIntent, MONTHS, programIn(), titleOf(), word() (+77 more)

### Community 1 - "journeyArt.ts"
Cohesion: 0.08
Nodes (23): ARCH, BOAT, BUSH, FOG_PALETTE, FOG_PROPS, fogIsle(), GULL, HUT (+15 more)

### Community 2 - "ChoiceApp"
Cohesion: 0.19
Nodes (18): ChoiceApp(), assistantSay(), handleIntent(), handleMilestone(), onConfirm(), onEditSave(), onSubmit(), openChat() (+10 more)

### Community 3 - "JourneySection.tsx"
Cohesion: 0.06
Nodes (28): src_components_home_journey_module, bezier(), Box, FOG, Ghost, HALF, ISLE_1, ISLE_1_SIZE (+20 more)

### Community 4 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 6 - "TopicWorkspace.tsx"
Cohesion: 0.11
Nodes (30): downloadMarkdown(), escape(), generateCards(), generateNotes(), inline(), markdownToHtml(), materialAsked(), MaterialKind (+22 more)

### Community 7 - "Dashboard.tsx"
Cohesion: 0.06
Nodes (64): react, Profile, CompareView(), CompareViewProps, Icon(), IconName, src_components_choice_layout_module, CompareRow (+56 more)

### Community 8 - "AuthGate.tsx"
Cohesion: 0.16
Nodes (9): nextConfig, next, metadata, src_components_account_account_module, Account, AccountContext, AuthGate(), store (+1 more)

### Community 9 - "Globe.tsx"
Cohesion: 0.13
Nodes (22): Program, PROGRAMS, arcDeg(), decodeWorld(), frameCountry(), Globe(), GlobeProps, Land (+14 more)

### Community 10 - "PixelDuck.tsx"
Cohesion: 0.15
Nodes (14): src_components_duck_pixel_duck_module, BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels() (+6 more)

### Community 11 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "GraphCanvas.tsx"
Cohesion: 0.22
Nodes (12): Beacon, Beacons(), clamp(), Drag, dropSelection(), GraphCanvas(), Popover, PopoverCard() (+4 more)

### Community 13 - "prepData.ts"
Cohesion: 0.07
Nodes (31): useAccount(), Props, UserMenu(), ENT_AREAS, ENT_CHECKS, ENT_SETS, ENT_SKILLS, ENT_TOPICS (+23 more)

### Community 14 - "JourneySection"
Cohesion: 0.18
Nodes (13): signalArc(), boatDistance(), clamp01(), JourneySection(), lerp(), place(), pointAt(), routeAt() (+5 more)

### Community 15 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 16 - "localAuth.ts"
Cohesion: 0.19
Nodes (8): auth, Account, derive(), localAuth, publicPart(), startSession(), toHex(), remoteAuth

### Community 17 - "package.json"
Cohesion: 0.07
Nodes (25): dependencies, next, react, react-dom, devDependencies, openapi-typescript, @types/node, @types/react (+17 more)

### Community 18 - "prepModel.ts"
Cohesion: 0.09
Nodes (28): DIAGNOSTIC_8_QUESTIONS, DiagnosticQuestion, DiagnosticResultSummary, Evidence, ExamId, Misconception, savedPrograms(), SetStatus (+20 more)

### Community 19 - "SetDetail.tsx"
Cohesion: 0.11
Nodes (35): useVertical(), src_components_prep_prep_module, EXAM_IDS, formatShort(), SETS, skillById(), STATE_LABEL, StudySet (+27 more)

### Community 20 - "layout.tsx"
Cohesion: 0.14
Nodes (12): ref_next_font_google, ref_next_navigation, src_app_globals, intelOneMono, inter, metadata, raleway, ScrollToTopOnReload() (+4 more)

### Community 21 - "milestoneMarks.ts"
Cohesion: 0.21
Nodes (15): undoMilestone(), undoTestDate(), chosenTestDates(), doneMilestones(), listeners, markMilestone(), NO_DATES, NO_MARKS (+7 more)

### Community 22 - "DuckLane.tsx"
Cohesion: 0.14
Nodes (13): src_components_home_duck_lane_module, BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight, PARACHUTE (+5 more)

### Community 23 - "LoginView.tsx"
Cohesion: 0.20
Nodes (8): metadata, AuthErrorCode, EMAIL_RE, PASSWORD_MIN, ERRORS, LoginView(), Mode, safeNext()

### Community 24 - "store.ts"
Cohesion: 0.15
Nodes (11): StateBackend, adoptLegacy(), cache, DEVICE, flush(), flushOnExit(), localBackend, pending (+3 more)

### Community 25 - "fieldValue"
Cohesion: 0.29
Nodes (8): editField(), extract(), fieldValue(), nextMissing(), placeholderFor(), applyToProfile(), onEditField(), showChat()

### Community 26 - "app/page.tsx"
Cohesion: 0.13
Nodes (18): metadata, src_components_home_aura_module, copy, CursorAura(), RADIUS, src_components_home_home_module, src_components_home_layers_module, LayerStack() (+10 more)

### Community 27 - "FooterDucks.tsx"
Cohesion: 0.38
Nodes (5): src_components_home_footer_module, FooterDucks(), POND, TUFT, SCENE_PALETTE

### Community 28 - "TransitionLink.tsx"
Cohesion: 0.50
Nodes (4): ref_next_link, TransitionLink(), TransitionLinkProps, usePageTransition()

### Community 29 - "glintMap"
Cohesion: 0.32
Nodes (8): glintMap(), islandSlice(), islandTop(), noise(), radius(), IslandBody(), Water(), usePoolImage()

### Community 30 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 31 - "remoteAuth.ts"
Cohesion: 0.32
Nodes (5): AuthError, User, call(), fail(), StudentCtx

### Community 32 - "Closing.tsx"
Cohesion: 0.12
Nodes (14): ANGLER, Closing(), FLOAT, GROUND_WIDE, LAKE, src_components_home_closing_module, PALETTE, ROD_BENT (+6 more)

### Community 33 - "prepAssistant.ts"
Cohesion: 0.38
Nodes (11): addDays(), ASSISTANT_PROMPTS, assistantReply(), examOf(), findDeadline(), minutesPerDay(), openSkills(), plan() (+3 more)

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

### Community 40 - "localSource.ts"
Cohesion: 0.10
Nodes (28): initialModel(), reviveModel(), ChanceFact, EMPTY_STATE, ExamPace, glowOf(), ProgramChance, QuackState (+20 more)

### Community 41 - "ActivityGrid.tsx"
Cohesion: 0.67
Nodes (3): ActivityGrid(), ActivityDay, streak()

### Community 46 - "HeroLandscape.tsx"
Cohesion: 0.13
Nodes (17): Prop(), FLAG_A, FLAG_B, HALL, HeroLandscape(), mirror(), PACE, POND (+9 more)

### Community 48 - "FirstHint.tsx"
Cohesion: 0.17
Nodes (12): Entry, Help, HelpContext, HelpDialog(), HelpDuck(), HelpProvider(), HelpState, Opened (+4 more)

### Community 53 - "assistant.ts"
Cohesion: 0.12
Nodes (21): acknowledge(), CONFIRM_REPLY, EMPTY_PROFILE, FieldKey, FIELDS, FieldStatus, labelOf(), MissingKey (+13 more)

### Community 58 - "ChoiceApp.tsx"
Cohesion: 0.15
Nodes (14): ChatMessage(), ChatMessageProps, ChatMsg, src_components_choice_choice_module, ChatItem, GREETINGS, LeftPanel, RightPanel (+6 more)

## Knowledge Gaps
- **312 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+307 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 392 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `Dashboard.tsx` to `standing.ts`, `JourneySection.tsx`, `TopicWorkspace.tsx`, `AuthGate.tsx`, `Globe.tsx`, `PixelDuck.tsx`, `GraphCanvas.tsx`, `prepData.ts`, `JourneySection`, `package.json`, `prepModel.ts`, `SetDetail.tsx`, `layout.tsx`, `milestoneMarks.ts`, `DuckLane.tsx`, `LoginView.tsx`, `app/page.tsx`, `FooterDucks.tsx`, `TransitionLink.tsx`, `Closing.tsx`, `PageSky.tsx`, `localSource.ts`, `HeroLandscape.tsx`, `FirstHint.tsx`, `assistant.ts`, `ChoiceApp.tsx`?**
  _High betweenness centrality (0.342) - this node is a cross-community bridge._
- **Why does `PixelDuck()` connect `PixelDuck.tsx` to `Closing.tsx`, `standing.ts`, `JourneySection.tsx`, `PageSky.tsx`, `Dashboard.tsx`, `AuthGate.tsx`, `HeroLandscape.tsx`, `FirstHint.tsx`, `layout.tsx`, `assistant.ts`, `DuckLane.tsx`, `LoginView.tsx`, `FooterDucks.tsx`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `ChoiceApp()` connect `ChoiceApp` to `standing.ts`, `localSource.ts`, `AuthGate.tsx`, `milestoneMarks.ts`, `assistant.ts`, `fieldValue`, `ChoiceApp.tsx`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _312 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `standing.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.05733397037744864 - nodes in this community are weakly interconnected._
- **Should `journeyArt.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `JourneySection.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.06451612903225806 - nodes in this community are weakly interconnected._