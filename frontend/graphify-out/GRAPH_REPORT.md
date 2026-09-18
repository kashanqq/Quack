# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 60 files · ~64,465 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 427 nodes · 925 edges · 12 communities (11 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c042d46d`
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
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
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
8. `copy` - 11 edges
9. `Profile` - 10 edges
10. `formatShort()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `ActivityGrid()` --calls--> `formatShort()`  [EXTRACTED]
  src/components/dashboard/ActivityGrid.tsx → src/components/prep/prepData.ts
- `CalendarTab()` --calls--> `formatDate()`  [EXTRACTED]
  src/components/dashboard/CalendarTab.tsx → src/components/prep/prepData.ts
- `GuideCanvas()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts
- `TaskCanvas()` --calls--> `skillById()`  [EXTRACTED]
  src/components/prep/CurrentSet.tsx → src/components/prep/prepData.ts
- `Route()` --calls--> `useVertical()`  [EXTRACTED]
  src/components/prep/SetsView.tsx → src/components/prep/GraphCanvas.tsx

## Import Cycles
- None detected.

## Communities (12 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (40): acknowledge(), editField(), EMPTY_PROFILE, extract(), FieldKey, FIELDS, FieldStatus, fieldValue() (+32 more)

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (21): intelOneMono, inter, metadata, raleway, Mode, LETTERS, MENU_LABEL, MODES (+13 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (30): ActivityGrid(), downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp() (+22 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (29): clamp(), Drag, GraphCanvas(), Popover, PopoverCard(), Props, readStore(), ScaleContext (+21 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (82): Dashboard(), forecastScore(), Props, activityByDay(), calendar(), calendarEvents(), hardConflicts(), removalEffects() (+74 more)

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (46): Program, PROGRAMS, ChatDemo(), ChatDemoProps, ChatThreadProps, ChatTurn, copy, DIALOGUES (+38 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (12): arcDeg(), frameCountry(), Globe(), GlobeProps, Land, RawWorld, Ring, Selection (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (36): Profile, CompareView(), CompareViewProps, Icon(), IconName, budgetOf(), CompareRow, compareRows() (+28 more)

## Knowledge Gaps
- **144 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+139 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Program` connect `Community 15` to `Community 16`, `Community 18`, `Community 2`, `Community 7`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `Icon()` connect `Community 18` to `Community 0`, `Community 1`, `Community 2`, `Community 7`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `PROGRAMS` connect `Community 15` to `Community 16`, `Community 18`, `Community 7`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _144 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0593990216631726 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.10574712643678161 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08888888888888889 - nodes in this community are weakly interconnected._