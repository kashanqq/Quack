# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 84 files · ~82,612 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 646 nodes · 1387 edges · 49 communities (25 shown, 24 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2f7805ea`
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
- [[_COMMUNITY_graphify reference transcribe video and audio|graphify reference: transcribe video and audio]]
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

## God Nodes (most connected - your core abstractions)
1. `formatDate()` - 21 edges
2. `daysBetween()` - 20 edges
3. `Icon()` - 16 edges
4. `PixelDuck()` - 16 edges
5. `compilerOptions` - 16 edges
6. `copy` - 13 edges
7. `skillById()` - 12 edges
8. `setById()` - 12 edges
9. `computeStanding()` - 12 edges
10. `Profile` - 11 edges

## Surprising Connections (you probably didn't know these)
- `ChoiceApp()` --calls--> `useQuack()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/quack/source.ts
- `describeChange()` --calls--> `programById()`  [EXTRACTED]
  src/components/quack/localSource.ts → src/components/choice/programs.ts
- `CalendarTab()` --calls--> `formatDate()`  [EXTRACTED]
  src/components/dashboard/CalendarTab.tsx → src/components/prep/prepData.ts
- `Dashboard()` --calls--> `useQuack()`  [EXTRACTED]
  src/components/dashboard/Dashboard.tsx → src/components/quack/source.ts
- `hardConflicts()` --calls--> `formatDate()`  [EXTRACTED]
  src/components/dashboard/dashboardRules.ts → src/components/prep/prepData.ts

## Import Cycles
- None detected.

## Communities (49 total, 24 thin omitted)

### Community 2 - "localSource.ts"
Cohesion: 0.07
Nodes (56): downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp(), CalendarTab() (+48 more)

### Community 3 - "ProgramUi.tsx"
Cohesion: 0.06
Nodes (36): Account, AccountContext, AuthGate(), AuthApi, AuthError, AuthErrorCode, StateBackend, User (+28 more)

### Community 4 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 6 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (37): fieldValue(), ChancesCard(), examWord(), Props, ChangesFeed(), Props, Target, TARGET_LABEL (+29 more)

### Community 11 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 13 - "standing.ts"
Cohesion: 0.10
Nodes (32): ChatLine, CurrentSet(), Props, Now(), ASSISTANT_PROMPTS, Evidence, ExamId, Misconception (+24 more)

### Community 14 - "SkillGraph.tsx"
Cohesion: 0.07
Nodes (29): Beacon, clamp(), Drag, GraphCanvas(), Popover, PopoverCard(), Props, ScaleContext (+21 more)

### Community 15 - "CalendarTab.tsx"
Cohesion: 0.10
Nodes (24): acknowledge(), editField(), EMPTY_PROFILE, extract(), FieldKey, FIELDS, FieldStatus, labelOf() (+16 more)

### Community 16 - "SetsView.tsx"
Cohesion: 0.10
Nodes (24): ActivityGrid(), ActivityDay, streak(), ForecastChart(), PAD, Props, useWidth(), CHECKS (+16 more)

### Community 17 - "Icon.tsx"
Cohesion: 0.10
Nodes (21): Prop(), FooterDucks(), POND, TUFT, FLAG_A, FLAG_B, GROUND, HALL (+13 more)

### Community 18 - "prepAssistant.ts"
Cohesion: 0.13
Nodes (23): Profile, budgetOf(), CompareRow, evaluate(), Evaluation, Factor, FactorStatus, formatEur() (+15 more)

### Community 20 - "prepData.ts"
Cohesion: 0.12
Nodes (13): CursorAura(), RADIUS, HeroTitle(), Point, LayerStack(), Billing, PricingPlans(), Roadmap() (+5 more)

### Community 21 - "graphify reference: extra exports and benchmark"
Cohesion: 0.10
Nodes (16): readiness(), ChatMessage(), ChatMessageProps, ChatMsg, ChatItem, ChoiceApp(), GREETINGS, LeftPanel (+8 more)

### Community 23 - "programs.ts"
Cohesion: 0.12
Nodes (16): useAccount(), intelOneMono, inter, metadata, raleway, Props, UserMenu(), ScrollToTopOnReload() (+8 more)

### Community 24 - "Sidebar.tsx"
Cohesion: 0.15
Nodes (15): BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels(), SLEEPING (+7 more)

### Community 25 - "graphify reference: query, path, explain"
Cohesion: 0.13
Nodes (15): arcDeg(), frameCountry(), Globe(), GlobeProps, Land, OPEN_COUNTRIES, pinsFor(), RawWorld (+7 more)

### Community 27 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.16
Nodes (12): Program, PROGRAMS, ChatDemo(), QuackSection(), TABS, Reveal(), RevealProps, TempoDucks() (+4 more)

### Community 28 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.15
Nodes (14): Icon(), IconName, ChatSummary, Mode, Sidebar(), SidebarProps, SidebarTab, TABS (+6 more)

### Community 29 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.14
Nodes (15): Overview(), PaceCard(), Programs(), Props, conflicts(), ExamOutlook, EXAMS, milestones() (+7 more)

### Community 30 - "graphify reference: GitHub clone and cross-repo merge"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 31 - "graphify reference: transcribe video and audio"
Cohesion: 0.18
Nodes (12): forecastSeries(), SET_STATUS_LABEL, SETS, clampGap(), columnScale(), isNow(), Props, Route() (+4 more)

### Community 32 - "CLAUDE.md"
Cohesion: 0.36
Nodes (12): CheckCanvas(), addDays(), assistantReply(), examOf(), findDeadline(), minutesPerDay(), openSkills(), plan() (+4 more)

### Community 33 - ".claude/CLAUDE.md"
Cohesion: 0.18
Nodes (10): BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight, PARACHUTE, ROPE (+2 more)

### Community 34 - "extraction-spec.md"
Cohesion: 0.20
Nodes (8): Cloud, CLOUD_A, CLOUD_B, CLOUDS, PageSky(), PALETTE, Pass, WEDGE

### Community 35 - "copy.ts"
Cohesion: 0.60
Nodes (4): CompareView(), CompareViewProps, compareRows(), compareSummary()

## Knowledge Gaps
- **199 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+194 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PixelDuck()` connect `Sidebar.tsx` to `.claude/CLAUDE.md`, `extraction-spec.md`, `ProgramUi.tsx`, `CalendarTab.tsx`, `Icon.tsx`, `prepData.ts`, `programs.ts`, `graphify reference: commit hook and native CLAUDE.md integration`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `store` connect `ProgramUi.tsx` to `localSource.ts`, `What You Must Do When Invoked`, `standing.ts`, `SkillGraph.tsx`, `graphify reference: extra exports and benchmark`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `Icon()` connect `graphify reference: commit hook and native CLAUDE.md integration` to `localSource.ts`, `copy.ts`, `What You Must Do When Invoked`, `standing.ts`, `CalendarTab.tsx`, `prepAssistant.ts`, `graphify reference: extra exports and benchmark`, `programs.ts`, `graphify reference: incremental update and cluster-only`, `graphify reference: transcribe video and audio`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _199 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `localSource.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.07117255504352278 - nodes in this community are weakly interconnected._
- **Should `ProgramUi.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.05513784461152882 - nodes in this community are weakly interconnected._
- **Should `compilerOptions` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._