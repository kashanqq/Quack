# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 59 files · ~37,713 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 420 nodes · 925 edges · 15 communities (14 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `263c6b92`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
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
9. `setById()` - 10 edges
10. `proposedSet()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Dashboard()` --calls--> `readiness()`  [EXTRACTED]
  src/components/dashboard/Dashboard.tsx → src/components/prep/prepModel.ts
- `CurrentSet()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts
- `CurrentSet()` --calls--> `closed()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepModel.ts
- `GuideCanvas()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts
- `TaskCanvas()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts

## Import Cycles
- None detected.

## Communities (15 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (39): acknowledge(), editField(), EMPTY_PROFILE, extract(), FieldKey, FIELDS, FieldStatus, fieldValue() (+31 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (22): intelOneMono, inter, metadata, raleway, ProfileToggle(), Mode, LETTERS, MENU_LABEL (+14 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (48): ActivityGrid(), downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp() (+40 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (61): GuideCanvas(), TaskCanvas(), clamp(), Drag, FitToWidth(), GraphCanvas(), Popover, PopoverCard() (+53 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (36): Icon(), IconName, ChatLine, Props, ForecastChart(), PAD, Props, useWidth() (+28 more)

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
Cohesion: 0.09
Nodes (32): Profile, CompareView(), CompareViewProps, budgetOf(), CompareRow, compareRows(), compareSummary(), evaluate() (+24 more)

## Knowledge Gaps
- **141 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+136 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Program` connect `Community 12` to `Community 2`, `Community 5`, `Community 7`, `Community 16`, `Community 18`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `Icon()` connect `Community 7` to `Community 0`, `Community 1`, `Community 2`, `Community 5`, `Community 18`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `PROGRAMS` connect `Community 12` to `Community 16`, `Community 18`, `Community 5`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _141 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06095791001451379 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.1010752688172043 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08080808080808081 - nodes in this community are weakly interconnected._