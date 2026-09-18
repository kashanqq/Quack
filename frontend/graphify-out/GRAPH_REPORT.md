# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 58 files · ~36,166 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 406 nodes · 887 edges · 25 communities (24 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ad1b5bfa`
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

## God Nodes (most connected - your core abstractions)
1. `formatDate()` - 16 edges
2. `compilerOptions` - 16 edges
3. `Dashboard()` - 14 edges
4. `Icon()` - 13 edges
5. `Overview()` - 12 edges
6. `daysBetween()` - 12 edges
7. `day()` - 11 edges
8. `Profile` - 10 edges
9. `setById()` - 10 edges
10. `proposedSet()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Dashboard()` --calls--> `readiness()`  [EXTRACTED]
  src/components/dashboard/Dashboard.tsx → src/components/prep/prepModel.ts
- `CurrentSet()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts
- `GuideCanvas()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts
- `TaskCanvas()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts
- `ForecastChart()` --calls--> `day()`  [EXTRACTED]
  src/components/prep/ForecastChart.tsx → src/components/prep/prepData.ts

## Import Cycles
- None detected.

## Communities (25 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (16): ChatMessage(), ChatMessageProps, ChatMsg, ChatItem, GREETINGS, LeftPanel, RightPanel, Session (+8 more)

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (21): intelOneMono, inter, metadata, raleway, ProfileToggle(), Mode, LETTERS, MODES (+13 more)

### Community 2 - "Community 2"
Cohesion: 0.50
Nodes (7): downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp()

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (43): ActivityGrid(), CalendarTab(), KIND_LABEL, MONTHS, WEEKDAYS, Dashboard(), forecastScore(), Props (+35 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.14
Nodes (13): useNodeDrag(), AREAS, Misconception, Skill, SKILLS, SkillState, along(), BASE (+5 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.23
Nodes (14): savedPrograms(), acceptSet(), initialModel(), makeCurrent(), PREP_SUBS, PREP_TABS, PrepModel, PrepSub (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (11): ChatLine, GuideCanvas(), Props, TaskCanvas(), GUIDELINES, skillById(), STATE_LABEL, AnswerResult (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.31
Nodes (7): Overview(), Programs(), Props, conflicts(), milestones(), realismShift(), requirements()

### Community 10 - "Community 10"
Cohesion: 0.33
Nodes (6): ForecastChart(), PAD, Props, useWidth(), ForecastPoint, TODAY

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "Community 12"
Cohesion: 0.18
Nodes (11): Program, PROGRAMS, ChatDemo(), QuackSection(), TABS, Reveal(), RevealProps, UniCarousel() (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.27
Nodes (6): copy, CursorAura(), Roadmap(), STEPS, StepState, SiteHeader()

### Community 14 - "Community 14"
Cohesion: 0.22
Nodes (12): day(), forecastSeries(), SET_STATUS_LABEL, SETS, disputeMisconception(), readiness(), setStatus(), Props (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (14): ChatDemoProps, ChatThreadProps, ChatTurn, DIALOGUES, BEAT, BODY, COLORS, FEET (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.18
Nodes (10): Globe(), GlobeProps, Land, RawWorld, Ring, Selection, COUNTRY_RU, countryRu() (+2 more)

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (12): BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight, PARACHUTE, pixels() (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (23): Profile, CompareView(), CompareViewProps, Icon(), budgetOf(), CompareRow, compareRows(), compareSummary() (+15 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (20): acknowledge(), editField(), EMPTY_PROFILE, extract(), FieldKey, FIELDS, FieldStatus, fieldValue() (+12 more)

### Community 20 - "Community 20"
Cohesion: 0.15
Nodes (11): DEMO_SAVED, Evidence, ExamRequirement, Guideline, Milestone, MisconceptionStatus, MONTHS, MONTHS_SHORT (+3 more)

### Community 21 - "Community 21"
Cohesion: 0.17
Nodes (10): IconName, LevelDot(), ProgramActions, ChatSummary, Sidebar(), SidebarProps, SidebarTab, TABS (+2 more)

### Community 23 - "Community 23"
Cohesion: 0.22
Nodes (7): Drag, GraphCanvas(), Props, readStore(), ScaleContext, View, writeStore()

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (4): readiness(), ChoiceApp(), ChoiceRoot(), metadata

## Knowledge Gaps
- **137 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+132 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Program` connect `Community 12` to `Community 3`, `Community 9`, `Community 16`, `Community 18`, `Community 20`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `Icon()` connect `Community 18` to `Community 1`, `Community 3`, `Community 7`, `Community 8`, `Community 9`, `Community 14`, `Community 19`, `Community 21`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `PROGRAMS` connect `Community 12` to `Community 16`, `Community 18`, `Community 20`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _137 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.10144927536231885 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.10574712643678161 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.08928571428571429 - nodes in this community are weakly interconnected._