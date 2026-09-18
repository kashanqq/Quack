# Graph Report - frontend  (2026-09-19)

## Corpus Check
- 88 files · ~97,554 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 707 nodes · 1547 edges · 56 communities (32 shown, 24 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.8)
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

## God Nodes (most connected - your core abstractions)
1. `daysBetween()` - 24 edges
2. `formatDate()` - 22 edges
3. `formatShort()` - 19 edges
4. `Icon()` - 17 edges
5. `PixelDuck()` - 17 edges
6. `compilerOptions` - 16 edges
7. `skillById()` - 15 edges
8. `copy` - 14 edges
9. `computeStanding()` - 12 edges
10. `Profile` - 11 edges

## Surprising Connections (you probably didn't know these)
- `ForecastChart()` --calls--> `Line`  [INFERRED]
  src/components/prep/ForecastChart.tsx → src/components/prep/TopicWorkspace.tsx
- `renderMarkdown()` --calls--> `flush()`  [INFERRED]
  src/components/prep/materials.tsx → src/components/account/store.ts
- `SkillDetails()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/SetsView.tsx → src/components/prep/prepData.ts
- `ChoiceApp()` --calls--> `useQuack()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/quack/source.ts
- `ProgramDrawer()` --calls--> `programById()`  [EXTRACTED]
  src/components/choice/ProgramUi.tsx → src/components/choice/programs.ts

## Import Cycles
- None detected.

## Communities (56 total, 24 thin omitted)

### Community 2 - "localSource.ts"
Cohesion: 0.16
Nodes (29): calendar(), hardConflicts(), Important(), addDays(), ASSISTANT_PROMPTS, assistantReply(), examOf(), findDeadline() (+21 more)

### Community 3 - "ProgramUi.tsx"
Cohesion: 0.06
Nodes (35): Account, AccountContext, AuthGate(), AuthApi, AuthError, AuthErrorCode, StateBackend, User (+27 more)

### Community 4 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 6 - "What You Must Do When Invoked"
Cohesion: 0.15
Nodes (16): fieldValue(), programById(), initialModel(), reviveModel(), EMPTY_STATE, glowOf(), QuackState, describeChange() (+8 more)

### Community 11 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 13 - "standing.ts"
Cohesion: 0.11
Nodes (28): Now(), Evidence, ExamId, Misconception, savedPrograms(), setById(), SetStatus, SkillState (+20 more)

### Community 14 - "SkillGraph.tsx"
Cohesion: 0.11
Nodes (19): useNodeDrag(), AREAS, Skill, SetGraph(), along(), autoLayout(), BASE, edgePath() (+11 more)

### Community 15 - "CalendarTab.tsx"
Cohesion: 0.18
Nodes (9): Beacon, clamp(), Drag, GraphCanvas(), Popover, PopoverCard(), Props, ScaleContext (+1 more)

### Community 16 - "SetsView.tsx"
Cohesion: 0.10
Nodes (30): ForecastChart(), PAD, Props, useWidth(), Overview(), Props, conflicts(), day() (+22 more)

### Community 17 - "Icon.tsx"
Cohesion: 0.18
Nodes (9): Cloud, CLOUD_A, CLOUD_B, CLOUDS, PageSky(), PALETTE, Pass, WEDGE (+1 more)

### Community 18 - "prepAssistant.ts"
Cohesion: 0.13
Nodes (21): Profile, budgetOf(), CompareRow, evaluate(), Evaluation, Factor, FactorStatus, formatEur() (+13 more)

### Community 20 - "prepData.ts"
Cohesion: 0.13
Nodes (15): arcDeg(), frameCountry(), Globe(), GlobeProps, Land, OPEN_COUNTRIES, pinsFor(), RawWorld (+7 more)

### Community 21 - "graphify reference: extra exports and benchmark"
Cohesion: 0.11
Nodes (22): acknowledge(), editField(), EMPTY_PROFILE, extract(), FieldKey, FIELDS, FieldStatus, labelOf() (+14 more)

### Community 23 - "programs.ts"
Cohesion: 0.12
Nodes (16): useAccount(), intelOneMono, inter, metadata, raleway, Props, UserMenu(), ScrollToTopOnReload() (+8 more)

### Community 24 - "Sidebar.tsx"
Cohesion: 0.13
Nodes (16): BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight, PARACHUTE, Prop() (+8 more)

### Community 25 - "graphify reference: query, path, explain"
Cohesion: 0.08
Nodes (22): ANGLER, FLOAT, GROUND_WIDE, LAKE, PALETTE, ROD_BENT, ROD_STRAIGHT, SPLASH (+14 more)

### Community 27 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.16
Nodes (11): Program, PROGRAMS, ChatDemo(), ChatDemoProps, ChatThreadProps, QuackSection(), TABS, UniCarousel() (+3 more)

### Community 28 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.12
Nodes (18): Icon(), IconName, ChatSummary, Mode, Sidebar(), SidebarProps, SidebarTab, TABS (+10 more)

### Community 29 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.12
Nodes (24): useVertical(), EXAMS, formatShort(), SET_STATUS_LABEL, STATE_LABEL, StudySet, rankSets(), setStatus() (+16 more)

### Community 30 - "graphify reference: GitHub clone and cross-repo merge"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (18): readiness(), ChatMessage(), ChatMessageProps, ChatMsg, ChatItem, ChoiceApp(), GREETINGS, LeftPanel (+10 more)

### Community 32 - "CLAUDE.md"
Cohesion: 0.22
Nodes (14): downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp(), CalendarTab() (+6 more)

### Community 33 - ".claude/CLAUDE.md"
Cohesion: 0.18
Nodes (11): BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels(), SLEEPING (+3 more)

### Community 34 - "extraction-spec.md"
Cohesion: 0.16
Nodes (9): Closing(), CursorAura(), RADIUS, HeroLandscape(), HeroTitle(), Point, Roadmap(), STEPS (+1 more)

### Community 35 - "copy.ts"
Cohesion: 0.18
Nodes (11): CompareView(), CompareViewProps, compareRows(), compareSummary(), Entry, FirstHint(), HelpContext, HelpEntries (+3 more)

### Community 49 - "Community 49"
Cohesion: 0.31
Nodes (10): Dashboard(), Props, calendarEvents(), removalEffects(), unionExams(), watchList(), PaceCard(), readiness() (+2 more)

### Community 50 - "Community 50"
Cohesion: 0.19
Nodes (10): Tempo, ChatTurn, copy, DIALOGUES, FooterDucks(), Billing, PricingPlans(), SiteFooter() (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.08
Nodes (32): downloadMarkdown(), escape(), generateCards(), generateNotes(), markdownToHtml(), materialAsked(), MaterialKind, newId() (+24 more)

### Community 52 - "Community 52"
Cohesion: 0.14
Nodes (15): ActivityGrid(), activityByDay(), ActivityDay, CalendarKind, Conflict, Demand, ExamId, examLabel() (+7 more)

### Community 53 - "Community 53"
Cohesion: 0.26
Nodes (11): Level, ChanceFact, ExamPace, PaceLevel, ProgramChance, Standing, StandingAlert, clamp() (+3 more)

### Community 54 - "Community 54"
Cohesion: 0.17
Nodes (9): ChancesCard(), examWord(), Props, ChangesFeed(), Props, Target, TARGET_LABEL, TONE_ICON (+1 more)

### Community 55 - "Community 55"
Cohesion: 0.36
Nodes (7): Draft, factChange(), firstBaseline(), needs(), plan(), targetsChange(), LEVEL_RANK

## Knowledge Gaps
- **221 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+216 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PixelDuck()` connect `.claude/CLAUDE.md` to `extraction-spec.md`, `copy.ts`, `ProgramUi.tsx`, `Icon.tsx`, `graphify reference: extra exports and benchmark`, `programs.ts`, `Sidebar.tsx`, `graphify reference: query, path, explain`, `graphify reference: add a URL and watch a folder`, `graphify reference: commit hook and native CLAUDE.md integration`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `Icon()` connect `graphify reference: commit hook and native CLAUDE.md integration` to `CLAUDE.md`, `copy.ts`, `SetsView.tsx`, `Community 49`, `prepAssistant.ts`, `Community 51`, `graphify reference: extra exports and benchmark`, `Community 54`, `programs.ts`, `graphify reference: incremental update and cluster-only`, `Community 31`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `store` connect `ProgramUi.tsx` to `copy.ts`, `What You Must Do When Invoked`, `standing.ts`, `SkillGraph.tsx`, `CalendarTab.tsx`, `Community 49`, `Community 31`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _221 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ProgramUi.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.05870020964360587 - nodes in this community are weakly interconnected._
- **Should `compilerOptions` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._
- **Should `standing.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.10804597701149425 - nodes in this community are weakly interconnected._