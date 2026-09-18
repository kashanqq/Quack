# Graph Report - frontend  (2026-09-19)

## Corpus Check
- 88 files · ~98,273 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 712 nodes · 1565 edges · 63 communities (39 shown, 24 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c9c2a485`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_dashboardRules.ts|dashboardRules.ts]]
- [[_COMMUNITY_ChoiceApp.tsx|ChoiceApp.tsx]]
- [[_COMMUNITY_localSource.ts|localSource.ts]]
- [[_COMMUNITY_ProgramUi.tsx|ProgramUi.tsx]]
- [[_COMMUNITY_compilerOptions|compilerOptions]]
- [[_COMMUNITY_react|react]]
- [[_COMMUNITY_What You Must Do When Invoked|What You Must Do When Invoked]]
- [[_COMMUNITY_HeroLandscape.tsx|HeroLandscape.tsx]]
- [[_COMMUNITY_apppage.tsx|app/page.tsx]]
- [[_COMMUNITY_Globe.tsx|Globe.tsx]]
- [[_COMMUNITY_PixelDuck.tsx|PixelDuck.tsx]]
- [[_COMMUNITY_Quack! — frontend|Quack! — frontend]]
- [[_COMMUNITY_prepModel.ts|prepModel.ts]]
- [[_COMMUNITY_standing.ts|standing.ts]]
- [[_COMMUNITY_SkillGraph.tsx|SkillGraph.tsx]]
- [[_COMMUNITY_CalendarTab.tsx|CalendarTab.tsx]]
- [[_COMMUNITY_SetsView.tsx|SetsView.tsx]]
- [[_COMMUNITY_Icon.tsx|Icon.tsx]]
- [[_COMMUNITY_prepAssistant.ts|prepAssistant.ts]]
- [[_COMMUNITY_PageSky.tsx|PageSky.tsx]]
- [[_COMMUNITY_prepData.ts|prepData.ts]]
- [[_COMMUNITY_graphify reference extra exports and benchmark|graphify reference: extra exports and benchmark]]
- [[_COMMUNITY_package.json|package.json]]
- [[_COMMUNITY_programs.ts|programs.ts]]
- [[_COMMUNITY_Sidebar.tsx|Sidebar.tsx]]
- [[_COMMUNITY_graphify reference query, path, explain|graphify reference: query, path, explain]]
- [[_COMMUNITY_FooterDucks.tsx|FooterDucks.tsx]]
- [[_COMMUNITY_graphify reference add a URL and watch a folder|graphify reference: add a URL and watch a folder]]
- [[_COMMUNITY_graphify reference commit hook and native CLAUDE.md integration|graphify reference: commit hook and native CLAUDE.md integration]]
- [[_COMMUNITY_graphify reference incremental update and cluster-only|graphify reference: incremental update and cluster-only]]
- [[_COMMUNITY_graphify reference GitHub clone and cross-repo merge|graphify reference: GitHub clone and cross-repo merge]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_CLAUDE|CLAUDE.md]]
- [[_COMMUNITY_.claudeCLAUDE|.claude/CLAUDE.md]]
- [[_COMMUNITY_extraction-spec|extraction-spec.md]]
- [[_COMMUNITY_copy.ts|copy.ts]]
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

## God Nodes (most connected - your core abstractions)
1. `daysBetween()` - 24 edges
2. `formatDate()` - 21 edges
3. `Icon()` - 18 edges
4. `PixelDuck()` - 18 edges
5. `formatShort()` - 18 edges
6. `skillById()` - 17 edges
7. `compilerOptions` - 16 edges
8. `copy` - 14 edges
9. `closed()` - 12 edges
10. `computeStanding()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `renderMarkdown()` --calls--> `flush()`  [INFERRED]
  src/components/prep/materials.tsx → src/components/account/store.ts
- `SkillDetails()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/SetsView.tsx → src/components/prep/prepData.ts
- `ChoiceApp()` --calls--> `useQuack()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/quack/source.ts
- `describeChange()` --calls--> `programById()`  [EXTRACTED]
  src/components/quack/localSource.ts → src/components/choice/programs.ts
- `ActivityGrid()` --calls--> `formatShort()`  [EXTRACTED]
  src/components/dashboard/ActivityGrid.tsx → src/components/prep/prepData.ts

## Import Cycles
- None detected.

## Communities (63 total, 24 thin omitted)

### Community 2 - "localSource.ts"
Cohesion: 0.27
Nodes (18): Important(), addDays(), ASSISTANT_PROMPTS, assistantReply(), examOf(), findDeadline(), minutesPerDay(), openSkills() (+10 more)

### Community 3 - "ProgramUi.tsx"
Cohesion: 0.23
Nodes (7): AuthError, AuthErrorCode, ERRORS, LoginView(), Mode, safeNext(), metadata

### Community 4 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 6 - "What You Must Do When Invoked"
Cohesion: 0.11
Nodes (24): fieldValue(), STATE_LABEL, ChanceFact, EMPTY_STATE, ExamPace, glowOf(), ProgramChance, QuackState (+16 more)

### Community 11 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 13 - "standing.ts"
Cohesion: 0.15
Nodes (17): Evidence, SETS, SetStatus, SKILLS, StudySet, AnswerResult, answerTask(), closed() (+9 more)

### Community 14 - "SkillGraph.tsx"
Cohesion: 0.07
Nodes (30): Beacon, clamp(), Drag, GraphCanvas(), Popover, PopoverCard(), Props, ScaleContext (+22 more)

### Community 15 - "CalendarTab.tsx"
Cohesion: 0.22
Nodes (12): acknowledge(), editField(), EMPTY_PROFILE, extract(), MissingKey, nextMissing(), placeholderFor(), planReply() (+4 more)

### Community 16 - "SetsView.tsx"
Cohesion: 0.10
Nodes (25): DUCK_TEMPO, Now(), Overview(), Props, conflicts(), day(), DEMO_SAVED, ExamOutlook (+17 more)

### Community 17 - "Icon.tsx"
Cohesion: 0.09
Nodes (23): Prop(), FLAG_A, FLAG_B, HALL, HeroLandscape(), PACE, POND, TEMPOS (+15 more)

### Community 18 - "prepAssistant.ts"
Cohesion: 0.12
Nodes (23): budgetOf(), CompareRow, evaluate(), Evaluation, Factor, FactorStatus, formatEur(), Level (+15 more)

### Community 20 - "prepData.ts"
Cohesion: 0.12
Nodes (16): Program, arcDeg(), frameCountry(), Globe(), GlobeProps, Land, OPEN_COUNTRIES, pinsFor() (+8 more)

### Community 21 - "graphify reference: extra exports and benchmark"
Cohesion: 0.13
Nodes (12): FieldKey, FIELDS, FieldStatus, labelOf(), profileItems(), CustomScrollbar(), CustomScrollbarProps, GROUPS (+4 more)

### Community 23 - "programs.ts"
Cohesion: 0.12
Nodes (16): useAccount(), intelOneMono, inter, metadata, raleway, Props, UserMenu(), ScrollToTopOnReload() (+8 more)

### Community 24 - "Sidebar.tsx"
Cohesion: 0.10
Nodes (20): BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels(), SLEEPING (+12 more)

### Community 25 - "graphify reference: query, path, explain"
Cohesion: 0.14
Nodes (12): ANGLER, FLOAT, GROUND_WIDE, LAKE, PALETTE, ROD_BENT, ROD_STRAIGHT, SPLASH (+4 more)

### Community 27 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.16
Nodes (13): ChatDemo(), ChatDemoProps, ChatThreadProps, ChatTurn, copy, DIALOGUES, QuackSection(), TABS (+5 more)

### Community 28 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.17
Nodes (10): ChatSummary, Sidebar(), SidebarProps, SidebarTab, TABS, DASH_TABS, DashTab, PREP_SUBS (+2 more)

### Community 29 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.15
Nodes (18): useVertical(), monthStarts(), disputeMisconception(), makeCurrent(), planFor(), proposedSet(), readiness(), setStatus() (+10 more)

### Community 30 - "graphify reference: GitHub clone and cross-repo merge"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 31 - "Community 31"
Cohesion: 0.12
Nodes (13): readiness(), ChatMessage(), ChatMessageProps, ChatMsg, ChatItem, ChoiceApp(), GREETINGS, LeftPanel (+5 more)

### Community 32 - "CLAUDE.md"
Cohesion: 0.20
Nodes (15): downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp(), CalendarTab() (+7 more)

### Community 33 - ".claude/CLAUDE.md"
Cohesion: 0.21
Nodes (11): StateBackend, adoptLegacy(), cache, DEVICE, flush(), flushOnExit(), localBackend, pending (+3 more)

### Community 34 - "extraction-spec.md"
Cohesion: 0.19
Nodes (7): Closing(), HeroTitle(), Point, LayerStack(), Roadmap(), STEPS, StepState

### Community 35 - "copy.ts"
Cohesion: 0.38
Nodes (6): Profile, CompareView(), CompareViewProps, compareRows(), compareSummary(), FirstHint()

### Community 49 - "Community 49"
Cohesion: 0.21
Nodes (11): ExamId, savedPrograms(), acceptSet(), initialModel(), PrepSub, reviveModel(), subFor(), INTROS (+3 more)

### Community 50 - "Community 50"
Cohesion: 0.21
Nodes (6): CursorAura(), RADIUS, Billing, PricingPlans(), SiteHeader(), metadata

### Community 51 - "Community 51"
Cohesion: 0.08
Nodes (33): downloadMarkdown(), escape(), generateCards(), generateNotes(), markdownToHtml(), materialAsked(), MaterialKind, newId() (+25 more)

### Community 52 - "Community 52"
Cohesion: 0.13
Nodes (23): ActivityGrid(), Dashboard(), Props, activityByDay(), ActivityDay, calendar(), calendarEvents(), CalendarKind (+15 more)

### Community 53 - "Community 53"
Cohesion: 0.20
Nodes (17): Conflict, EXAMS, forecastSeries(), StandingAlert, addDays(), alertsFor(), clamp(), computeStanding() (+9 more)

### Community 54 - "Community 54"
Cohesion: 0.16
Nodes (11): Icon(), ChancesCard(), examWord(), Props, ChangesFeed(), Props, Target, TARGET_LABEL (+3 more)

### Community 55 - "Community 55"
Cohesion: 0.20
Nodes (10): EXAMS, SET_STATUS_LABEL, Due, DUE_TEXT, plannedDates(), Props, SetDetail(), STATUS_TEXT (+2 more)

### Community 56 - "Community 56"
Cohesion: 0.22
Nodes (7): Account, AccountContext, AuthGate(), store, ChoiceRoot(), metadata, HelpProvider()

### Community 57 - "Community 57"
Cohesion: 0.18
Nodes (9): Entry, Help, HelpContext, HelpDialog(), HelpDuck(), HelpState, Opened, Props (+1 more)

### Community 58 - "Community 58"
Cohesion: 0.24
Nodes (5): AuthApi, User, localAuth, remoteAuth, StudentCtx

### Community 59 - "Community 59"
Cohesion: 0.28
Nodes (5): Account, derive(), publicPart(), startSession(), toHex()

### Community 60 - "Community 60"
Cohesion: 0.22
Nodes (8): IconName, Mode, LETTERS, MENU_LABEL, MODES, Topbar(), TopbarProps, SignalLevel

### Community 61 - "Community 61"
Cohesion: 0.33
Nodes (5): FooterDucks(), POND, TUFT, SCENE_PALETTE, SiteFooter()

### Community 62 - "Community 62"
Cohesion: 0.50
Nodes (3): morph(), ViewTransition, WithViewTransition

## Knowledge Gaps
- **225 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+220 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PixelDuck()` connect `Sidebar.tsx` to `extraction-spec.md`, `ProgramUi.tsx`, `SetsView.tsx`, `Icon.tsx`, `graphify reference: extra exports and benchmark`, `programs.ts`, `Community 56`, `Community 57`, `graphify reference: add a URL and watch a folder`, `Community 60`, `Community 61`, `graphify reference: query, path, explain`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `Icon()` connect `Community 54` to `CLAUDE.md`, `copy.ts`, `standing.ts`, `Community 60`, `SetsView.tsx`, `prepAssistant.ts`, `Community 51`, `Community 52`, `graphify reference: extra exports and benchmark`, `Community 55`, `programs.ts`, `graphify reference: commit hook and native CLAUDE.md integration`, `graphify reference: incremental update and cluster-only`, `Community 31`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `store` connect `Community 56` to `.claude/CLAUDE.md`, `ProgramUi.tsx`, `What You Must Do When Invoked`, `SkillGraph.tsx`, `Community 49`, `Community 52`, `Community 57`, `Community 31`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _225 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `compilerOptions` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._
- **Should `What You Must Do When Invoked` be split into smaller, more focused modules?**
  _Cohesion score 0.10984848484848485 - nodes in this community are weakly interconnected._
- **Should `SkillGraph.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.06825396825396825 - nodes in this community are weakly interconnected._