# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 42 files · ~44,046 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 16 file(s) not represented in the graph (top: .css 15, (none) 1)

## Summary
- 270 nodes · 509 edges · 10 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a28a2b81`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- assistant.ts
- react
- ChoiceApp.tsx
- compilerOptions
- package.json
- TransitionProvider.tsx
- DuckLane.tsx
- Globe.tsx
- Quack! — frontend
- app/page.tsx

## God Nodes (most connected - your core abstractions)
1. `react` - 24 edges
2. `ChoiceApp()` - 20 edges
3. `compilerOptions` - 16 edges
4. `copy` - 11 edges
5. `evaluate()` - 10 edges
6. `programById()` - 9 edges
7. `Globe()` - 8 edges
8. `Quack! — frontend` - 8 edges
9. `Profile` - 7 edges
10. `planReply()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `ChoiceApp()` --calls--> `fieldValue()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts
- `applyToProfile()` --calls--> `fieldValue()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts
- `showChat()` --calls--> `placeholderFor()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts
- `ChoiceApp()` --calls--> `extract()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts
- `ChoiceApp()` --calls--> `placeholderFor()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts

## Import Cycles
- None detected.

## Communities (10 total, 0 thin omitted)

### Community 0 - "assistant.ts"
Cohesion: 0.13
Nodes (25): acknowledge(), CONFIRM_REPLY, EMPTY_PROFILE, extract(), MissingKey, nextMissing(), placeholderFor(), planReply() (+17 more)

### Community 1 - "react"
Cohesion: 0.09
Nodes (32): react, ChatDemo(), ChatDemoProps, ChatThreadProps, ChatTurn, copy, DIALOGUES, src_components_home_layers_module (+24 more)

### Community 2 - "ChoiceApp.tsx"
Cohesion: 0.07
Nodes (49): FieldKey, FIELDS, fieldValue(), Profile, ChatMessage(), ChatMessageProps, ChatMsg, src_components_choice_choice_module (+41 more)

### Community 3 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 4 - "package.json"
Cohesion: 0.07
Nodes (25): nextConfig, dependencies, next, react, react-dom, devDependencies, @types/node, @types/react (+17 more)

### Community 5 - "TransitionProvider.tsx"
Cohesion: 0.13
Nodes (17): ref_next_font_google, ref_next_navigation, src_app_globals, intelOneMono, inter, metadata, raleway, Duck() (+9 more)

### Community 6 - "DuckLane.tsx"
Cohesion: 0.15
Nodes (13): src_components_home_duck_lane_module, BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight, PARACHUTE (+5 more)

### Community 7 - "Globe.tsx"
Cohesion: 0.17
Nodes (17): PROGRAMS, arcDeg(), decodeWorld(), frameCountry(), Globe(), GlobeProps, Land, src_components_home_globe_module (+9 more)

### Community 8 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 9 - "app/page.tsx"
Cohesion: 0.12
Nodes (17): ref_next_link, Topbar(), TopbarProps, src_components_home_aura_module, CursorAura(), RADIUS, src_components_home_footer_module, src_components_home_home_module (+9 more)

## Knowledge Gaps
- **103 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+98 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 124 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `react` to `ChoiceApp.tsx`, `package.json`, `TransitionProvider.tsx`, `DuckLane.tsx`, `Globe.tsx`, `app/page.tsx`?**
  _High betweenness centrality (0.456) - this node is a cross-community bridge._
- **Why does `ChoiceApp()` connect `assistant.ts` to `ChoiceApp.tsx`, `package.json`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _103 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `assistant.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.12962962962962962 - nodes in this community are weakly interconnected._
- **Should `react` be split into smaller, more focused modules?**
  _Cohesion score 0.08985200845665962 - nodes in this community are weakly interconnected._
- **Should `ChoiceApp.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07401129943502825 - nodes in this community are weakly interconnected._
- **Should `compilerOptions` be split into smaller, more focused modules?**
  _Cohesion score 0.10526315789473684 - nodes in this community are weakly interconnected._