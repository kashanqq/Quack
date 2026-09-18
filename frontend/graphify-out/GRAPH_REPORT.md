# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 75 files · ~76,247 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 551 nodes · 1271 edges · 27 communities (26 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `84d6bc50`
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
- [[_COMMUNITY_Community 26|Community 26]]

## God Nodes (most connected - your core abstractions)
1. `formatDate()` - 22 edges
2. `daysBetween()` - 20 edges
3. `Icon()` - 17 edges
4. `compilerOptions` - 16 edges
5. `Dashboard()` - 15 edges
6. `setById()` - 14 edges
7. `PixelDuck()` - 13 edges
8. `copy` - 13 edges
9. `programById()` - 12 edges
10. `Overview()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `ChoiceApp()` --calls--> `useQuack()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/quack/source.ts
- `describeChange()` --calls--> `programById()`  [EXTRACTED]
  src/components/quack/localSource.ts → src/components/choice/programs.ts
- `CalendarTab()` --calls--> `formatDate()`  [EXTRACTED]
  src/components/dashboard/CalendarTab.tsx → src/components/prep/prepData.ts
- `activityByDay()` --calls--> `daysBetween()`  [EXTRACTED]
  src/components/dashboard/dashboardRules.ts → src/components/prep/prepData.ts
- `Prop()` --calls--> `pixelRects()`  [EXTRACTED]
  src/components/home/DuckLane.tsx → src/components/home/PixelSprite.tsx

## Import Cycles
- None detected.

## Communities (27 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (16): ChatMessage(), ChatMessageProps, ChatMsg, ChatItem, GREETINGS, LeftPanel, RightPanel, Session (+8 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (23): intelOneMono, inter, metadata, raleway, IconName, Mode, LETTERS, MENU_LABEL (+15 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (45): Dashboard(), Props, calendar(), calendarEvents(), hardConflicts(), removalEffects(), unionExams(), watchList() (+37 more)

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (15): Tempo, copy, DIALOGUES, CursorAura(), RADIUS, FooterDucks(), LayerStack(), Billing (+7 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (17): useNodeDrag(), useVertical(), Skill, along(), autoLayout(), BASE, edgePath(), horizontalLayout() (+9 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (26): DEMO_SAVED, Evidence, ExamRequirement, Guideline, Milestone, Misconception, MisconceptionStatus, MONTHS (+18 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (16): BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight, PARACHUTE, Prop() (+8 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (21): acknowledge(), editField(), EMPTY_PROFILE, extract(), FieldKey, FIELDS, FieldStatus, labelOf() (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (14): POND, TUFT, FLAG_A, FLAG_B, GROUND, HALL, PACE, POND (+6 more)

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (22): Profile, budgetOf(), CompareRow, evaluate(), Evaluation, Factor, FactorStatus, formatEur() (+14 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (15): AREAS, day(), requirements(), SET_STATUS_LABEL, disputeMisconception(), setStatus(), clampGap(), columnScale() (+7 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (26): downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp(), CalendarTab() (+18 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (13): Program, ChatDemo(), ChatDemoProps, ChatThreadProps, ChatTurn, QuackSection(), TABS, Reveal() (+5 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (16): PROGRAMS, arcDeg(), frameCountry(), Globe(), GlobeProps, Land, OPEN_COUNTRIES, pinsFor() (+8 more)

### Community 17 - "Community 17"
Cohesion: 0.15
Nodes (12): BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels(), SLEEPING (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.19
Nodes (10): CompareView(), CompareViewProps, Icon(), compareRows(), compareSummary(), ChangesFeed(), Props, Target (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.33
Nodes (4): readiness(), ChoiceApp(), ChoiceRoot(), metadata

### Community 20 - "Community 20"
Cohesion: 0.09
Nodes (32): fieldValue(), ChancesCard(), examWord(), Props, initialModel(), reviveModel(), ChanceFact, EMPTY_STATE (+24 more)

### Community 21 - "Community 21"
Cohesion: 0.16
Nodes (11): ChatLine, GuideCanvas(), Props, TaskCanvas(), GUIDELINES, skillById(), STATE_LABEL, AnswerResult (+3 more)

### Community 23 - "Community 23"
Cohesion: 0.15
Nodes (11): Beacon, clamp(), Drag, GraphCanvas(), Popover, PopoverCard(), Props, readStore() (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.18
Nodes (9): ChatSummary, Sidebar(), SidebarProps, SidebarTab, TABS, DASH_TABS, DashTab, PREP_SUBS (+1 more)

### Community 25 - "Community 25"
Cohesion: 0.25
Nodes (9): ActivityGrid(), ActivityDay, streak(), ForecastChart(), PAD, Props, useWidth(), ForecastPoint (+1 more)

### Community 26 - "Community 26"
Cohesion: 0.20
Nodes (8): Cloud, CLOUD_A, CLOUD_B, CLOUDS, PageSky(), PALETTE, Pass, WEDGE

## Knowledge Gaps
- **180 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+175 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PixelDuck()` connect `Community 17` to `Community 0`, `Community 1`, `Community 3`, `Community 8`, `Community 10`, `Community 15`, `Community 26`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `Icon()` connect `Community 18` to `Community 0`, `Community 1`, `Community 2`, `Community 7`, `Community 9`, `Community 12`, `Community 13`, `Community 14`, `Community 20`, `Community 21`, `Community 24`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `Program` connect `Community 15` to `Community 2`, `Community 7`, `Community 12`, `Community 14`, `Community 16`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _180 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09538461538461539 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09425287356321839 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.11673469387755102 - nodes in this community are weakly interconnected._