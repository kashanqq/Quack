# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 67 files · ~71,209 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 496 nodes · 1164 edges · 18 communities (17 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `df50e4cf`
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
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 22|Community 22]]

## God Nodes (most connected - your core abstractions)
1. `formatDate()` - 22 edges
2. `daysBetween()` - 20 edges
3. `Icon()` - 16 edges
4. `compilerOptions` - 16 edges
5. `Dashboard()` - 15 edges
6. `setById()` - 14 edges
7. `programById()` - 12 edges
8. `Overview()` - 12 edges
9. `day()` - 12 edges
10. `proposedSet()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `ChoiceApp()` --calls--> `useQuack()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/quack/source.ts
- `describeChange()` --calls--> `programById()`  [EXTRACTED]
  src/components/quack/localSource.ts → src/components/choice/programs.ts
- `ActivityGrid()` --calls--> `formatShort()`  [EXTRACTED]
  src/components/dashboard/ActivityGrid.tsx → src/components/prep/prepData.ts
- `CalendarTab()` --calls--> `formatDate()`  [EXTRACTED]
  src/components/dashboard/CalendarTab.tsx → src/components/prep/prepData.ts
- `Dashboard()` --calls--> `formatDate()`  [EXTRACTED]
  src/components/dashboard/Dashboard.tsx → src/components/prep/prepData.ts

## Import Cycles
- None detected.

## Communities (18 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.15
Nodes (10): ChatMessage(), ChatMessageProps, ChatMsg, ChatItem, GREETINGS, LeftPanel, RightPanel, Session (+2 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (24): intelOneMono, inter, metadata, raleway, Icon(), IconName, LETTERS, MENU_LABEL (+16 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (38): LevelBadge(), ActivityGrid(), Dashboard(), Props, activityByDay(), ActivityDay, calendar(), calendarEvents() (+30 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (31): Beacon, clamp(), Drag, GraphCanvas(), Popover, PopoverCard(), Props, readStore() (+23 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (16): dependencies, next, react, react-dom, devDependencies, @types/node, @types/react, @types/react-dom (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (79): Program, ChatLine, CurrentSet(), GuideCanvas(), Props, TaskCanvas(), ForecastChart(), PAD (+71 more)

### Community 9 - "Community 9"
Cohesion: 0.22
Nodes (12): acknowledge(), editField(), EMPTY_PROFILE, extract(), FieldStatus, MissingKey, nextMissing(), placeholderFor() (+4 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (12): FieldKey, FIELDS, fieldValue(), labelOf(), ProfileItem, profileItems(), CustomScrollbar(), CustomScrollbarProps (+4 more)

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (19): budgetOf(), evaluate(), formatEur(), Level, LEVEL_LABEL, programById(), LevelDot(), ProgramActions (+11 more)

### Community 14 - "Community 14"
Cohesion: 0.22
Nodes (14): downloadIcs(), escape(), googleCalendarUrl(), icsFile(), nextDay(), pad(), stamp(), CalendarTab() (+6 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (44): ChatDemo(), ChatDemoProps, ChatThreadProps, ChatTurn, copy, DIALOGUES, CursorAura(), RADIUS (+36 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (13): PROGRAMS, arcDeg(), frameCountry(), Globe(), GlobeProps, Land, RawWorld, Ring (+5 more)

### Community 18 - "Community 18"
Cohesion: 0.24
Nodes (10): Profile, CompareView(), CompareViewProps, CompareRow, compareRows(), compareSummary(), Evaluation, Factor (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.33
Nodes (4): readiness(), ChoiceApp(), ChoiceRoot(), metadata

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (43): ChancesCard(), examWord(), Props, ChangesFeed(), Props, Target, TARGET_LABEL, TONE_ICON (+35 more)

## Knowledge Gaps
- **153 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+148 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Program` connect `Community 7` to `Community 2`, `Community 15`, `Community 16`, `Community 18`, `Community 20`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `Icon()` connect `Community 1` to `Community 2`, `Community 7`, `Community 10`, `Community 12`, `Community 14`, `Community 18`, `Community 20`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `PROGRAMS` connect `Community 16` to `Community 18`, `Community 7`, `Community 15`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _153 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09879032258064516 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09302325581395349 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._