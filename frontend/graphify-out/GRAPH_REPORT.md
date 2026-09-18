# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 58 files · ~38,120 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 420 nodes · 911 edges · 19 communities (18 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cd89bb76`
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
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 22|Community 22]]

## God Nodes (most connected - your core abstractions)
1. `formatDate()` - 16 edges
2. `compilerOptions` - 16 edges
3. `Dashboard()` - 14 edges
4. `Icon()` - 13 edges
5. `Overview()` - 12 edges
6. `day()` - 12 edges
7. `daysBetween()` - 12 edges
8. `Profile` - 10 edges
9. `formatShort()` - 10 edges
10. `setById()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `ActivityGrid()` --calls--> `formatShort()`  [EXTRACTED]
  src/components/dashboard/ActivityGrid.tsx → src/components/prep/prepData.ts
- `Dashboard()` --calls--> `readiness()`  [EXTRACTED]
  src/components/dashboard/Dashboard.tsx → src/components/prep/prepModel.ts
- `CurrentSet()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts
- `CurrentSet()` --calls--> `closed()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepModel.ts
- `GuideCanvas()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts

## Import Cycles
- None detected.

## Communities (19 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (23): acknowledge(), editField(), EMPTY_PROFILE, extract(), FieldKey, FIELDS, FieldStatus, fieldValue() (+15 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (23): intelOneMono, inter, metadata, raleway, Icon(), IconName, Mode, LETTERS (+15 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (47): ActivityGrid(), downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp() (+39 more)

### Community 3 - "Community 3"
Cohesion: 0.10
Nodes (19): ChatMessage(), ChatMessageProps, ChatMsg, ChatItem, GREETINGS, LeftPanel, RightPanel, Session (+11 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (28): clamp(), Drag, GraphCanvas(), Popover, PopoverCard(), Props, readStore(), ScaleContext (+20 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (66): ChatLine, GuideCanvas(), Props, TaskCanvas(), ForecastChart(), PAD, Props, useWidth() (+58 more)

### Community 8 - "Community 8"
Cohesion: 0.33
Nodes (4): readiness(), ChoiceApp(), ChoiceRoot(), metadata

### Community 9 - "Community 9"
Cohesion: 0.60
Nodes (4): CompareView(), CompareViewProps, compareRows(), compareSummary()

### Community 10 - "Community 10"
Cohesion: 0.50
Nodes (3): morph(), ViewTransition, WithViewTransition

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "Community 12"
Cohesion: 0.18
Nodes (11): Program, PROGRAMS, ChatDemo(), QuackSection(), TABS, Reveal(), RevealProps, UniCarousel() (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.27
Nodes (6): copy, CursorAura(), Roadmap(), STEPS, StepState, SiteHeader()

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
Nodes (21): Profile, budgetOf(), CompareRow, evaluate(), Evaluation, Factor, FactorStatus, formatEur() (+13 more)

## Knowledge Gaps
- **143 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+138 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Program` connect `Community 12` to `Community 16`, `Community 18`, `Community 2`, `Community 7`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `Icon()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 7`, `Community 9`, `Community 18`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `PROGRAMS` connect `Community 12` to `Community 16`, `Community 18`, `Community 7`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _143 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09659090909090909 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08176100628930817 - nodes in this community are weakly interconnected._