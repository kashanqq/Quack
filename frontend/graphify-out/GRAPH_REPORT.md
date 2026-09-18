# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 83 files · ~79,353 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 599 nodes · 1368 edges · 26 communities (25 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `024c3687`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

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
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]

## God Nodes (most connected - your core abstractions)
1. `formatDate()` - 22 edges
2. `daysBetween()` - 20 edges
3. `Icon()` - 17 edges
4. `compilerOptions` - 16 edges
5. `Dashboard()` - 15 edges
6. `PixelDuck()` - 15 edges
7. `setById()` - 14 edges
8. `copy` - 13 edges
9. `programById()` - 12 edges
10. `Overview()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `ChoiceApp()` --calls--> `useQuack()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/quack/source.ts
- `ProgramDrawer()` --calls--> `programById()`  [EXTRACTED]
  src/components/choice/ProgramUi.tsx → src/components/choice/programs.ts
- `describeChange()` --calls--> `fieldValue()`  [EXTRACTED]
  src/components/quack/localSource.ts → src/components/choice/assistant.ts
- `CalendarTab()` --calls--> `formatDate()`  [EXTRACTED]
  src/components/dashboard/CalendarTab.tsx → src/components/prep/prepData.ts
- `Dashboard()` --calls--> `removalEffects()`  [EXTRACTED]
  src/components/dashboard/Dashboard.tsx → src/components/dashboard/dashboardRules.ts

## Import Cycles
- None detected.

## Communities (26 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.17
Nodes (8): CursorAura(), RADIUS, HeroTitle(), Point, LayerStack(), Roadmap(), STEPS, StepState

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (23): useAccount(), intelOneMono, inter, metadata, raleway, Mode, LETTERS, MENU_LABEL (+15 more)

### Community 2 - "Community 2"
Cohesion: 0.11
Nodes (48): Program, Dashboard(), calendar(), calendarEvents(), hardConflicts(), unionExams(), CurrentSet(), Important() (+40 more)

### Community 3 - "Community 3"
Cohesion: 0.18
Nodes (9): ChatDemoProps, ChatThreadProps, ChatTurn, copy, DIALOGUES, Billing, PricingPlans(), SiteHeader() (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (17): useNodeDrag(), useVertical(), AREAS, Skill, along(), autoLayout(), BASE, edgePath() (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.15
Nodes (18): Evidence, savedPrograms(), SetStatus, SkillState, StudySet, Task, acceptSet(), disputeMisconception() (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.18
Nodes (10): BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight, PARACHUTE, ROPE (+2 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (38): acknowledge(), editField(), EMPTY_PROFILE, extract(), FieldKey, FIELDS, FieldStatus, fieldValue() (+30 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (25): Prop(), FLAG_A, FLAG_B, GROUND, HALL, HeroLandscape(), PACE, POND (+17 more)

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (59): Profile, CompareView(), CompareViewProps, Icon(), IconName, budgetOf(), CompareRow, compareRows() (+51 more)

### Community 13 - "Community 13"
Cohesion: 0.19
Nodes (11): SET_STATUS_LABEL, SETS, SKILLS, clampGap(), columnScale(), isNow(), Props, RouteColumn() (+3 more)

### Community 14 - "Community 14"
Cohesion: 0.22
Nodes (14): downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp(), CalendarTab() (+6 more)

### Community 15 - "Community 15"
Cohesion: 0.21
Nodes (9): ChatDemo(), QuackSection(), TABS, Reveal(), RevealProps, UniCarousel(), UniCarouselProps, useRotator() (+1 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (16): PROGRAMS, arcDeg(), frameCountry(), Globe(), GlobeProps, Land, OPEN_COUNTRIES, pinsFor() (+8 more)

### Community 17 - "Community 17"
Cohesion: 0.18
Nodes (11): BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels(), SLEEPING (+3 more)

### Community 18 - "Community 18"
Cohesion: 0.20
Nodes (8): DEMO_SAVED, ExamRequirement, Guideline, Milestone, Misconception, MisconceptionStatus, MONTHS, MONTHS_SHORT

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (36): Account, AccountContext, AuthGate(), AuthApi, AuthError, AuthErrorCode, StateBackend, User (+28 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (28): programById(), initialModel(), reviveModel(), ChanceFact, EMPTY_STATE, ExamPace, glowOf(), PaceLevel (+20 more)

### Community 21 - "Community 21"
Cohesion: 0.16
Nodes (11): ChatLine, GuideCanvas(), Props, TaskCanvas(), GUIDELINES, skillById(), STATE_LABEL, AnswerResult (+3 more)

### Community 23 - "Community 23"
Cohesion: 0.18
Nodes (9): Beacon, clamp(), Drag, GraphCanvas(), Popover, PopoverCard(), Props, ScaleContext (+1 more)

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (5): FooterDucks(), POND, TUFT, SCENE_PALETTE, SiteFooter()

### Community 25 - "Community 25"
Cohesion: 0.23
Nodes (10): ActivityGrid(), ActivityDay, streak(), ForecastChart(), PAD, Props, useWidth(), ForecastPoint (+2 more)

## Knowledge Gaps
- **193 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+188 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PixelDuck()` connect `Community 17` to `Community 0`, `Community 1`, `Community 3`, `Community 8`, `Community 10`, `Community 19`, `Community 24`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `store` connect `Community 19` to `Community 5`, `Community 7`, `Community 9`, `Community 12`, `Community 20`, `Community 23`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `Program` connect `Community 2` to `Community 16`, `Community 18`, `Community 12`, `Community 15`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _193 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09655172413793103 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.10633484162895927 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._