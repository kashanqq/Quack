# Graph Report - frontend  (2026-09-18)

## Corpus Check
- 61 files · ~59,912 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 20 file(s) not represented in the graph (top: .css 18, (none) 2)

## Summary
- 387 nodes · 666 edges · 25 communities (20 shown, 5 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ce1de613`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ChoiceApp.tsx
- What You Must Do When Invoked
- programs.ts
- compilerOptions
- package.json
- TransitionProvider.tsx
- HeroLandscape.tsx
- Globe.tsx
- Quack! — frontend
- react
- graphify reference: extra exports and benchmark
- graphify reference: query, path, explain
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- .claude/CLAUDE.md
- extraction-spec.md
- DuckLane.tsx
- PixelDuck.tsx
- PageSky.tsx
- FooterDucks.tsx
- PixelSprite.tsx

## God Nodes (most connected - your core abstractions)
1. `react` - 30 edges
2. `ChoiceApp()` - 20 edges
3. `compilerOptions` - 16 edges
4. `copy` - 13 edges
5. `What You Must Do When Invoked` - 12 edges
6. `/graphify` - 11 edges
7. `evaluate()` - 10 edges
8. `PixelDuck()` - 10 edges
9. `programById()` - 9 edges
10. `Globe()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `showChat()` --calls--> `placeholderFor()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts
- `Prop()` --calls--> `pixelRects()`  [EXTRACTED]
  src/components/home/DuckLane.tsx → src/components/home/PixelSprite.tsx
- `ChoiceApp()` --calls--> `extract()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts
- `ChoiceApp()` --calls--> `fieldValue()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts
- `ChoiceApp()` --calls--> `placeholderFor()`  [EXTRACTED]
  src/components/choice/ChoiceApp.tsx → src/components/choice/assistant.ts

## Import Cycles
- None detected.

## Communities (25 total, 5 thin omitted)

### Community 0 - "ChoiceApp.tsx"
Cohesion: 0.08
Nodes (44): acknowledge(), CONFIRM_REPLY, EMPTY_PROFILE, extract(), FieldKey, FIELDS, fieldValue(), MissingKey (+36 more)

### Community 1 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 2 - "programs.ts"
Cohesion: 0.12
Nodes (29): Profile, CompareView(), CompareViewProps, Icon(), IconName, budgetOf(), CompareRow, compareRows() (+21 more)

### Community 3 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 4 - "package.json"
Cohesion: 0.07
Nodes (25): nextConfig, dependencies, next, react, react-dom, devDependencies, @types/node, @types/react (+17 more)

### Community 5 - "TransitionProvider.tsx"
Cohesion: 0.10
Nodes (20): ref_next_font_google, ref_next_navigation, src_app_globals, intelOneMono, inter, metadata, raleway, Topbar() (+12 more)

### Community 6 - "HeroLandscape.tsx"
Cohesion: 0.14
Nodes (14): FLAG_A, FLAG_B, GROUND, HALL, mirror(), PACE, POND, REEDS (+6 more)

### Community 7 - "Globe.tsx"
Cohesion: 0.13
Nodes (22): Program, PROGRAMS, arcDeg(), decodeWorld(), frameCountry(), Globe(), GlobeProps, Land (+14 more)

### Community 8 - "Quack! — frontend"
Cohesion: 0.22
Nodes (8): graphify, Quack! — frontend, Адаптивность, Запуск, Стек, Страницы, Структура, Что имитируется и где подключать бэкенд

### Community 9 - "react"
Cohesion: 0.07
Nodes (38): react, metadata, src_components_home_aura_module, ChatDemo(), ChatDemoProps, ChatThreadProps, ChatTurn, copy (+30 more)

### Community 10 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 11 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 12 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 13 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 14 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 20 - "DuckLane.tsx"
Cohesion: 0.17
Nodes (11): src_components_home_duck_lane_module, BALLOON, COLORS, DuckLane(), DuckLaneProps, FLAME, Flight, PARACHUTE (+3 more)

### Community 21 - "PixelDuck.tsx"
Cohesion: 0.18
Nodes (11): src_components_home_pixel_duck_module, BEAT, BODY, COLORS, FEET, PixelDuck(), PixelDuckProps, pixels() (+3 more)

### Community 22 - "PageSky.tsx"
Cohesion: 0.18
Nodes (9): Cloud, CLOUD_A, CLOUD_B, CLOUDS, PageSky(), PALETTE, Pass, WEDGE (+1 more)

### Community 23 - "FooterDucks.tsx"
Cohesion: 0.28
Nodes (7): ref_next_link, src_components_home_footer_module, FooterDucks(), POND, TUFT, SCENE_PALETTE, SiteFooter()

### Community 24 - "PixelSprite.tsx"
Cohesion: 0.33
Nodes (6): Prop(), HeroLandscape(), Palette, pixelRects(), PixelSprite(), PixelSpriteProps

## Knowledge Gaps
- **173 isolated node(s):** `nextConfig`, `name`, `version`, `private`, `dev` (+168 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 209 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `react` to `ChoiceApp.tsx`, `programs.ts`, `package.json`, `TransitionProvider.tsx`, `HeroLandscape.tsx`, `Globe.tsx`, `DuckLane.tsx`, `PixelDuck.tsx`, `PageSky.tsx`, `FooterDucks.tsx`, `PixelSprite.tsx`?**
  _High betweenness centrality (0.334) - this node is a cross-community bridge._
- **Why does `ChoiceApp()` connect `ChoiceApp.tsx` to `package.json`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `next` connect `package.json` to `react`, `TransitionProvider.tsx`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **What connects `nextConfig`, `name`, `version` to the rest of the system?**
  _173 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ChoiceApp.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07918552036199095 - nodes in this community are weakly interconnected._
- **Should `What You Must Do When Invoked` be split into smaller, more focused modules?**
  _Cohesion score 0.07407407407407407 - nodes in this community are weakly interconnected._
- **Should `programs.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.12100840336134454 - nodes in this community are weakly interconnected._