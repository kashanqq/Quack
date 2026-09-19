# Архитектура памяти и ИИ — Quack\!

Версия 1.0-draft · 17.09.2026 · дополняет `product-logic.md` (ссылки вида «§N» — на него). Описывает, что система хранит об ученике, как это попадает в базу, как читается и где участвует языковая модель. Не описывает API-контракты и UI. Параметры названы именами, значения — в §12 «Конфиг».

&nbsp;

Метки: `[OPEN]` — параметр или решение, которое ещё не закрыто; `[B1]`/`[B2]`/`[B3]` — владелец по ролям из product-logic §10.6.

&nbsp;

---

## 0\. Тезисы

1. **Хранится модель ученика, а не история.** Сырьё — события: сообщения, ответы на задачи, действия. Ценность — то, что из них извлечено: какие навыки в каком состоянии, какие ошибки мышления активны и при каких условиях проявляются, где корень ошибок, как быстро ученик забывает. В контекст репетитора идёт эта модель плюс короткое окно диалога, а не переписка.  
2. **События — источник правды, граф — проекция.** Append-only лог в PostgreSQL; Neo4j пересобирается из него. Выход наблюдателя тоже сохраняется как событие, поэтому пересборка не требует языковой модели.  
3. **Репетитор учит, наблюдатель запоминает.** Модель, которая отвечает ученику, в граф не пишет. Извлечение — отдельный асинхронный процесс со своим промптом и версией.  
4. **Чат — основной источник по объёму, младший по доверию.** Ученик спрашивает, присылает решения, ошибается в разговоре — это самые частые свидетельства, но и самые шумные. Задачи и моки — контролируемый замер, который подтверждает и закрывает. Иерархия доверия зашита в правила (§4.3), а не в промпт.  
5. **Всё, что можно посчитать правилом, считается правилом.** Состояния, статусы заблуждений, корни, очередь сетов, прогноз — детерминированно, мгновенно, повторяемо. Модель — только там, где нужно понять текст или написать текст.  
6. **Ничего без доказательства.** Любое утверждение раскрывается до конкретного сообщения или задачи с ответом ученика. Ученик может оспорить одним действием.

### 0.1 Словарь (дополнение к §0 product-logic)

- **Событие** — запись в логе о действии ученика или системы; неизменяемая.  
- **Свидетельство (Evidence)** — факт о знаниях с весом и ссылкой на событие: «в событии 4412 ученик показал X».  
- **Состояние навыка (KnowledgeState)** — оценка навыка во времени: период полураспада, вероятность вспомнить сейчас, уверенность.  
- **Ярус доверия** — класс источника свидетельства (1 — мок и замер, 2 — задача и решение в чате, 3 — реплика в чате), определяет вес и право закрывать навык.  
- **Наблюдатель** — фоновый процесс с языковой моделью, который читает чат подготовки и предлагает свидетельства. Не отвечает ученику.  
- **Шаблон задачи (TaskTemplate)** — параметризованная задача с формулами верного ответа и дистракторов; из шаблона генерируются экземпляры.  
- **Экземпляр (TaskInstance)** — конкретная задача с подставленными параметрами; то, что видит ученик.  
- **Корень (ROOT\_CAUSE)** — связь свидетельства об ошибке в навыке X с навыком Y, из\-за которого ошибка произошла.  
- **Триггеры (triggers)** — агрегат условий, при которых у ученика проявляется заблуждение.  
- **Контекст топика** — собранный из графа блок, который репетитор получает на весь топик.

&nbsp;

---

## 1\. Хранилища и слои

### 1.1 Что где лежит

| Хранилище | Что | Почему здесь |
| :---- | :---- | :---- |
| **PostgreSQL** | `events` (лог); профиль — анкета, черты, резюме предпочтений; сохранённые программы; кэш программ; шаблоны и экземпляры задач; `seen_templates`; кэш сгенерированных текстов; `Summary` по сетам; read-модели для UI | транзакционность, простые выборки, всё, что не требует обхода связей |
| **Neo4j** | канонический слой (экзамены, области, навыки, зависимости, библиотека заблуждений, шаблоны как узлы); персональный слой (состояния, статусы заблуждений, свидетельства, корни, персональные узлы); база знаний о поступлении; `ExamFormat` | главные запросы — многошаговые обходы: заблуждение → навык → предпосылки → состояния → свидетельства; спуск по зависимостям; корни |
| **Neo4j vector index** | эмбеддинги `Misconception` (библиотечных и персональных) | канонизация персональных заблуждений против библиотеки. Другие эмбеддинги не хранятся: сообщения не эмбеддятся, задачи не эмбеддятся |

&nbsp;

Четыре слоя памяти:

&nbsp;

| Слой | Что | Где | Кто пишет | Кто читает |
| :---- | :---- | :---- | :---- | :---- |
| **Episodic** | сырые события | Postgres `events` | API | наблюдатель, replay, активность, провенанс |
| **Semantic** | навыки, состояния, заблуждения, свидетельства, корни | Neo4j | правила reconciliation | контекст, сеты, прогноз, выбор задач, отчёты |
| **Procedural** | как ученик учится: часы факт, темп, распределение классов ошибок | Postgres (агрегаты) \+ анкета | ежедневная агрегация | контекст, Quack |
| **Working** | контекст топика \+ строка сессии | in-memory / кэш | context assembler | репетитор |

### 1.2 Лог событий

events (

&nbsp;

&nbsp;&nbsp;id                BIGSERIAL PRIMARY KEY,

&nbsp;

&nbsp;&nbsp;student\_id        UUID NOT NULL,

&nbsp;

&nbsp;&nbsp;session\_id        UUID,               \-- сессия работы (открытие приложения → 30 мин тишины)

&nbsp;

&nbsp;&nbsp;exam\_id           TEXT,

&nbsp;

&nbsp;&nbsp;set\_id            UUID,

&nbsp;

&nbsp;&nbsp;topic\_skill\_id    TEXT,               \-- навык текущего топика, если применимо

&nbsp;

&nbsp;&nbsp;chat\_id           UUID,

&nbsp;

&nbsp;&nbsp;type              TEXT NOT NULL,

&nbsp;

&nbsp;&nbsp;payload           JSONB NOT NULL,

&nbsp;

&nbsp;&nbsp;occurred\_at       TIMESTAMPTZ NOT NULL,

&nbsp;

&nbsp;&nbsp;ingested\_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

&nbsp;

&nbsp;&nbsp;processed\_at      TIMESTAMPTZ,        \-- когда применено к графу

&nbsp;

&nbsp;&nbsp;extractor\_version TEXT,               \-- для observation.extracted

&nbsp;

&nbsp;&nbsp;source\_event\_ids  BIGINT\[\]            \-- для observation.extracted: какие сообщения обработаны

&nbsp;

)

&nbsp;

\-- индексы: (student\_id, occurred\_at), (chat\_id, processed\_at) WHERE processed\_at IS NULL, (type)

&nbsp;

Типы событий:

&nbsp;

| Тип | Payload | Меняет модель знаний |
| :---- | :---- | :---- |
| `message.user` | text | нет напрямую — через наблюдателя |
| `message.assistant` | text, `gave_task_instance_id?`, `hint_level?`, `referenced_skill_ids[]`, `mode` (explain / review / task) | нет; разметка репетитора помогает наблюдателю |
| `task.issued` | instance\_id, template\_id, skill\_id, mode, via (topic / mock / diagnostic / chat) | нет |
| `task.answered` | instance\_id, answer, time\_spent\_sec, mode, session\_minute, after\_guideline, hint\_level\_before | **да, синхронно** |
| `task.skipped`, `task.timed_out` | instance\_id, mode | след для темпа |
| `mock.started` / `mock.completed` | состав, raw\_score, scaled\_estimate?, `predicted_before` | completed — фиксирует прогноз для Brier |
| `diagnostic.progress` / `diagnostic.completed` | очередь спуска, бюджет, итог | да (через task.answered) |
| `observation.extracted` | выход наблюдателя (§8.1) | **да, правилом** |
| `observer.requested` | — | триггер наблюдателя вручную |
| `set.opened`, `set.completed`, `set.switched_by_user`, `set.deadline_changed` | set\_id, состав | сеты, контекст |
| `topic.opened`, `topic.completed` | topic\_skill\_id | контекст, триггер наблюдателя |
| `misconception.disputed` / `.undisputed` | misconception\_id | да |
| `skill.personal_created`, `misconception.personal_created` | описание узла | да |
| `misconception.canonized` | source\_event\_id, ordinal, skill\_id, canonical\_id, similarity, decided\_by | да — предложенное заблуждение сведено к существующему (§5.4) |
| `profile.updated` | field, value, by (assistant / user) | приоры; подборка |
| `program.saved` / `program.removed` | program\_id | требования, вехи |
| `milestone.done` | milestone\_id | вехи |
| `recommendation.accepted` / `.declined` | recommendation\_id, reason\_hash | Quack |
| `guideline.opened`, `explanation.opened` | skill\_id | только активность и `after_guideline` |

&nbsp;

Правило: всё, что влияет на модель знаний, обязано пройти через `events`. Read-модели (`messages`, `mock_attempts`) — материализация событий, не источник.

&nbsp;

---

## 2\. Схема графа (Neo4j)

### 2.1 Канонический слой — общий для всех, ученик не редактирует `[B1]`

(:Exam {id, name, max\_raw\_score})                      // SAT\_MATH, ENT\_MATH

&nbsp;

(:Area {id, exam\_id, name, score\_share: FLOAT})        // Algebra 0.35, …

&nbsp;

(:Skill {id, name, description, scope: 'canonical',

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;effort\_h: FLOAT,                              // часов на освоение с нуля до цели; вход прогноза даты

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;base\_half\_life\_h: FLOAT})                     // стартовый h для этого навыка (по умолчанию из конфига)

&nbsp;

(:Misconception {id, name, description, error\_class: 'computational'|'conceptual'|'attention'|'procedural',

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;exam\_specific: TEXT?,                  // если ловушка существует только в формате одного экзамена

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;embedding: LIST\<FLOAT\>, scope: 'library'})

&nbsp;

(:TaskTemplate {id, exam\_id, type: 'mcq4'|'mcq5'|'multi\_select'|'numeric',

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;difficulty: INT, tags: LIST\<STRING\>, time\_reference\_sec: INT,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;kind: 'template'|'manual'})            // manual — ручная задача с рисунком (§3.2)

&nbsp;

(:Exam)-\[:HAS\_AREA\]-\>(:Area)

&nbsp;

(:Area)-\[:HAS\_SKILL {weight: FLOAT}\]-\>(:Skill)         // вклад навыка в балл экзамена; Σ weight по экзамену \= max\_raw\_score

&nbsp;

(:Skill)-\[:REQUIRES {strength: FLOAT}\]-\>(:Skill)       // предпосылки; DAG; strength 0..1

&nbsp;

(:Misconception)-\[:ABOUT\]-\>(:Skill)

&nbsp;

(:TaskTemplate)-\[:TESTS {weight: FLOAT}\]-\>(:Skill)     // обычно один навык с weight 1.0

&nbsp;

(:TaskTemplate)-\[:TRAPS {distractor\_key: STRING}\]-\>(:Misconception)   // какой дистрактор к какому заблуждению

&nbsp;

**Общие навыки SAT / ЕНТ.** Навык, который по сути один в обоих экзаменах (квадратные уравнения, проценты), — один узел с двумя рёбрами `HAS_SKILL` от областей двух экзаменов, с разными `weight`. Формат экзамена учитывается не в навыке, а в состоянии (§4.6). Навыки, существующие только в одном экзамене (стереометрия в ЕНТ), — с одним ребром.

### 2.2 Персональный слой — на ученика

(:Student {id})

&nbsp;

(:KnowledgeState {exam\_id: TEXT,                        // для общих навыков — состояние на каждый экзамен

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;p\_at\_obs: FLOAT,                      // p на момент последнего наблюдения

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;half\_life\_h: FLOAT,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;evidence\_mass: FLOAT,                 // Σ weight всех свидетельств — вход confidence

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;n\_correct: INT, n\_incorrect: INT, n\_partial: INT,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;has\_strong: BOOL,                     // есть ли свидетельство яруса 1–2 этого экзамена

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;last\_observed\_at: DATETIME,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;confidence: FLOAT,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;source\_event\_id: BIGINT, created\_at: DATETIME})

&nbsp;

(:MisconceptionState {status: 'suspected'|'confirmed'|'resolved'|'disputed',

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;occurrence\_count: INT,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;strong\_count: INT,                // сколько свидетельств яруса 1–2

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;consecutive\_avoided: INT,         // подряд «ловушка была — не попал»

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;first\_seen, last\_seen, resolved\_at?, disputed\_at?,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;triggers: MAP})                   // §5.3

&nbsp;

(:Evidence {id, event\_id: BIGINT, kind: STRING, tier: 1|2|3, source: 'task'|'mock'|'diagnostic'|'chat'|'self\_report',

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;weight: FLOAT, direction: 1|-1|0,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;exam\_id: TEXT, summary: STRING?,            // summary — только для чатовых, ≤ 300 символов

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;// контекст ситуации:

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;task\_type?, difficulty?, tags?: LIST, mode?, time\_ratio?: FLOAT, session\_minute?: INT,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;after\_guideline?: BOOL, hint\_level\_before?: INT, topic\_skill\_id?, session\_id,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;observed\_at: DATETIME, ingested\_at: DATETIME, extractor\_version?: STRING})

&nbsp;

(:Skill {id, scope: 'personal', student\_id, name, description,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;task\_filter: MAP,                              // {tags: \[...\], difficulty: \[..\]} — фильтр шаблонов родителя

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;reason: STRING, created\_at})

&nbsp;

(:Misconception {id, scope: 'personal', student\_id, name, description, error\_class, embedding})

&nbsp;

(:Student)-\[:HAS\_STATE\]-\>(:KnowledgeState)-\[:FOR\]-\>(:Skill)     // текущее; на общий навык — два (по exam\_id)

&nbsp;

(:KnowledgeState)-\[:PREVIOUS\]-\>(:KnowledgeState)                // история

&nbsp;

(:Student)-\[:HAS\_MISC\_STATE\]-\>(:MisconceptionState)-\[:OF\]-\>(:Misconception)

&nbsp;

(:Evidence)-\[:SUPPORTS {direction}\]-\>(:Skill)

&nbsp;

(:Evidence)-\[:SUPPORTS\]-\>(:Misconception)

&nbsp;

(:Evidence)-\[:ROOT\_CAUSE {confidence: FLOAT, source: 'diagnostic'|'observer'|'rule'}\]-\>(:Skill)

&nbsp;

(:Evidence)-\[:FROM\_TEMPLATE\]-\>(:TaskTemplate)                    // для задачных свидетельств

&nbsp;

(:Skill {scope:'personal'})-\[:PART\_OF\]-\>(:Skill {scope:'canonical'})

&nbsp;

(:Misconception {scope:'personal'})-\[:ABOUT\]-\>(:Skill)

&nbsp;

Почему так:

&nbsp;

- **Заблуждение — общий узел, статус — персональный.** Библиотека одна на всех; у каждого ученика свой `MisconceptionState`. Иначе библиотека размножается на каждого.  
- **`KnowledgeState` — узел с историей, не свойство.** Тренд («последние три свидетельства хуже») и отчёт «до / после сета» считаются по цепочке `PREVIOUS`; в скаляре они потеряны.  
- **`Evidence` несёт контекст.** Из него считаются `triggers` (при каких условиях ошибается) без повторного обращения к событиям.  
- **`has_strong` и `evidence_mass`** — чтобы правила «нельзя закрыть навык одним чатом» и «confidence по сумме весов» считались за O(1).

### 2.3 База знаний о поступлении и ExamFormat `[B1 черновик, B2 дополняет]`

В том же графе, отдельные метки, без связей с персональным слоем. У каждого узла `source: URL`, `checked_at: DATE`, `is_demo: BOOL`.

&nbsp;

(:Exam)-\[:HAS\_SECTION\]-\>(:Section {n\_items, minutes, item\_types: MAP, scoring\_rule, calculator: BOOL, adaptive: BOOL,

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;area\_shares: MAP, difficulty\_shares: MAP, answer\_forms: LIST})

&nbsp;

(:Exam)-\[:HAS\_DATE\]-\>(:TestDate {date, registration\_deadline, late\_deadline?, source, checked\_at, is\_demo})

&nbsp;

(:Exam)-\[:HAS\_SCALE\]-\>(:ScaleTable {raw\_to\_scaled: MAP, note: 'оценочно'})

&nbsp;

(:Country {id, name})-\[:HAS\_ROUTE\]-\>(:AdmissionRoute {id, name, description})

&nbsp;

(:AdmissionRoute)-\[:REQUIRES\]-\>(:Requirement {type, exam\_id?, threshold?, comparator, description})

&nbsp;

(:Program {id})-\[:REQUIRES\]-\>(:Requirement)               // Program.id — ссылка на запись кэша программ в Postgres

&nbsp;

(:Program)-\[:HAS\_DEADLINE\]-\>(:Deadline {kind, date, round?, source, checked\_at, is\_demo})

&nbsp;

(:Fact {text, source, checked\_at, is\_demo})-\[:ABOUT\]-\>(любой узел выше)

&nbsp;

Доступ — только через инструменты (§9.5, §10.6). Ни ассистент, ни репетитор не отвечают о правилах, датах и требованиях из памяти модели.

### 2.4 Индексы и изоляция

CREATE VECTOR INDEX misc\_emb IF NOT EXISTS FOR (m:Misconception) ON m.embedding

&nbsp;

&nbsp;&nbsp;OPTIONS {indexConfig: {\`vector.dimensions\`: 1024, \`vector.similarity\_function\`: 'cosine'}};

&nbsp;

CREATE INDEX skill\_id      IF NOT EXISTS FOR (s:Skill) ON (s.id);

&nbsp;

CREATE INDEX template\_id   IF NOT EXISTS FOR (t:TaskTemplate) ON (t.id);

&nbsp;

CREATE INDEX evidence\_key  IF NOT EXISTS FOR (e:Evidence) ON (e.event\_id, e.skill\_id);   // идемпотентность

&nbsp;

CREATE INDEX ks\_student    IF NOT EXISTS FOR (k:KnowledgeState) ON (k.student\_id, k.exam\_id);

&nbsp;

CREATE INDEX ms\_status     IF NOT EXISTS FOR (m:MisconceptionState) ON (m.student\_id, m.status);

&nbsp;

Все запросы персонального слоя начинаются с `MATCH (st:Student {id: $student_id})`. Персональные узлы `Skill`/`Misconception` несут `student_id` и никогда не связываются между учениками — кросс-ученический слой в этом проекте не строится.

&nbsp;

---

## 3\. Задачи: шаблоны и ручные задачи `[B2 схема и слияние, все пишут]`

### 3.1 Шаблон

Основной источник задач — параметризованные шаблоны, не датасет готовых задач. Шаблон — это мини-программа: условие с параметрами, ограничения на параметры, формула верного ответа, формулы дистракторов с привязкой к заблуждениям. Разметка дистракторов живёт на шаблоне, поэтому в момент ответа ученика свидетельство получается чтением разметки, а не извлечением.

&nbsp;

{

&nbsp;

&nbsp;&nbsp;"id": "tpl.sat.alg.abs\_eq\_sum\_roots",

&nbsp;

&nbsp;&nbsp;"exam\_id": "SAT\_MATH", "type": "mcq4", "difficulty": 3,

&nbsp;

&nbsp;&nbsp;"skill\_id": "sat.alg.abs\_value\_eq",

&nbsp;

&nbsp;&nbsp;"tags": \["negative\_branch", "sum\_of\_roots"\],

&nbsp;

&nbsp;&nbsp;"time\_reference\_sec": 75,

&nbsp;

&nbsp;&nbsp;"params": {

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;"a": {"range": \[2, 5\]},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;"b": {"range": \[2, 12\]},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;"c": {"range": \[1, 9\]}

&nbsp;

&nbsp;&nbsp;},

&nbsp;

&nbsp;&nbsp;"constraints": \["(b \+ c) % a \== 0", "(b \- c) % a \== 0", "b \> c"\],

&nbsp;

&nbsp;&nbsp;"stem": "|{a}x − {b}| \= {c}. Чему равна сумма корней уравнения?",

&nbsp;

&nbsp;&nbsp;"correct": "2\*b/a",

&nbsp;

&nbsp;&nbsp;"distractors": \[

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"expr": "(b \+ c)/a",        "misconception\_id": "lib.abs\_single\_branch"},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"expr": "(b \- c)/a",        "misconception\_id": "lib.abs\_single\_branch"},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"expr": "-2\*b/a",           "misconception\_id": "lib.abs\_sign\_drop"},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"expr": "2\*c/a",            "misconception\_id": null}

&nbsp;

&nbsp;&nbsp;\],

&nbsp;

&nbsp;&nbsp;"solution": \["Раскрыть модуль: {a}x − {b} \= {c} или {a}x − {b} \= −{c}", "x₁ \= ({b}+{c})/{a}, x₂ \= ({b}−{c})/{a}", "Сумма \= 2·{b}/{a} \= {answer}"\]

&nbsp;

}

&nbsp;

Поля по типам:

&nbsp;

- `mcq4` / `mcq5` — `correct` одно выражение, `distractors` — 3 или 4, каждый с `misconception_id` или `null` («случайный»). Если дистракторов больше нужного, при генерации выбираются: сначала с заблуждениями, которые у ученика `confirmed`/`suspected`, затем остальные.  
- `multi_select` — `correct` — список выражений (все верные), `distractors` — неверные с привязкой, плюс `omission_traps`: `{"omit": "<выражение верного>", "misconception_id"}` — если ученик не выбрал этот верный вариант, это тоже размеченная ошибка.  
- `numeric` — `correct` выражение, `answer_forms` (допустимые записи: дробь, десятичная, диапазон точности), `trap_answers` — 2–3 выражения с привязкой к заблуждениям. Без ловушечных ответов numeric-задачи диагностику не дают.

&nbsp;

`tags` — содержательные признаки, по которым считаются `triggers` (§5.3) и строятся персональные узлы (§7). Заполняются один раз на шаблон.

### 3.2 Ручные задачи

Для навыков, где без рисунка нельзя (геометрия, графики функций), — ручные задачи с готовым SVG/PNG, той же схемой, что экземпляр (§3.3), но с `kind: 'manual'`, без параметров. Разметка дистракторов та же. Ориентир — 10–15 задач `[OPEN]`. Хранятся в графе как `TaskTemplate {kind:'manual'}` с единственным экземпляром.

### 3.3 Экземпляр

Генерируется из шаблона по seed: подстановка параметров, проверка ограничений, вычисление верного и дистракторов, проверка инвариантов, перемешивание вариантов. Хранится в Postgres:

&nbsp;

task\_instances(id, template\_id, seed, exam\_id, type, stem\_rendered, options JSONB,   \-- \[{key, text, correct, misconception\_id}\]

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;answer JSONB, trap\_answers JSONB, solution\_rendered, figure\_url?, created\_at)

&nbsp;

Событие `task.answered` ссылается на `instance_id`; свидетельство — на экземпляр (в Postgres) и на шаблон (`FROM_TEMPLATE` в графе).

### 3.4 Инварианты — проверяются автоматически при генерации

- ровно один верный вариант (`mcq`); заявленное множество верных (`multi_select`); одна величина с допустимыми записями (`numeric`);  
- все дистракторы попарно различны и не равны верному — если при данных параметрах совпали, seed отбрасывается;  
- значения в допустимом диапазоне (целые, если ограничение требует; без деления на ноль);  
- решение при подстановке сходится с `correct`;  
- нет дубля по `(template_id, seed)`.

&nbsp;

Шаблон принимается, если 50 случайных сидов проходят инварианты. Это заменяет ручной чек-лист по каждой задаче: проверяется один раз шаблон, а не каждая задача.

### 3.5 Откуда шаблоны

Смесь: калибровка формата и сложности по официальным практическим материалам; генерация шаблонов языковой моделью пачками по спецификации формата (§3.1) и библиотеке заблуждений (§5) → автоматический прогон по 50 сидам → ручная проверка стиля и языка (5 минут на шаблон вместо 5 минут на задачу). Ориентир: 2–3 шаблона на навык, \~100 шаблонов на два экзамена `[OPEN: объём]`.

### 3.6 Пул и повторы

`seen_templates(student_id, template_id, n_seen, last_seen_at)`. Выбор задачи предпочитает шаблоны с `n_seen = 0`; повтор шаблона с другими параметрами допускается с весом свидетельства `× seen_template_factor`. Экземпляр никогда не повторяется буквально. Исчерпание шаблонов навыка — пометка ученику и продолжение с повторами.

&nbsp;

---

## 4\. Состояние навыка

### 4.1 Модель забывания — half-life regression

Для каждого `KnowledgeState` хранятся `half_life_h` (h) и `last_observed_at`. Вероятность вспомнить сейчас не хранится, а вычисляется при чтении:

&nbsp;

p\_recall(now) \= 2 ^ ( −Δt / h ),   Δt \= now − last\_observed\_at (в часах)

&nbsp;

Обновление на каждое свидетельство (в Python, результат — новый узел состояния):

&nbsp;

correct:    h ← h · (1 \+ α · weight · difficulty\_factor)

&nbsp;

incorrect:  h ← h · max(0.25, 1 − β · weight)

&nbsp;

partial:    применить correct с weight·share и incorrect с weight·(1−share)

&nbsp;

затем       h ← clamp(h, h\_min, h\_max)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;p\_at\_obs ← (для correct) min(1, p\_recall(before) \+ (1 − p\_recall(before)) · weight · 0.5)

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(для incorrect) p\_recall(before) · (1 − weight · 0.5)

&nbsp;

`difficulty_factor` — сложность задачи по шкале экзамена, нормированная в `[0.7, 1.3]`; для чатовых свидетельств 1.0.

&nbsp;

Что даёт: нет фоновой джобы пересчёта; «просядет ли навык к тест-дате» — арифметика; `due_at = last_observed_at + h · log2(1 / p_target)` — момент, когда навык снова опустится ниже цели и должен вернуться в сет повторением.

### 4.2 Уверенность

confidence \= 1 − exp(−evidence\_mass / k) · g(разброс)

&nbsp;

evidence\_mass \= Σ weight по всем свидетельствам этого состояния

&nbsp;

g(разброс) \= 1 при согласованных исходах; до 1.5 при чередовании верно/неверно (снижает confidence)

&nbsp;

Считается по **сумме весов**, а не по числу свидетельств: пять реплик в чате по 0.4 — это 2.0, один мок — 1.0. Навык с одним свидетельством и `p = 0.9` — не «освоено», а «мало данных».

### 4.3 Ярусы доверия

| Ярус | Источник | weight | Сильное |
| :---- | :---- | :---- | :---- |
| 1 | замер, мок по сету / топику, мини-мок под заблуждение | 1.0 | да |
| 2 | задача в топике (свободная работа) | 0.8 | да |
| 2 | присланное в чате решение — шаг верный / шаг с явной ошибкой | 0.7 | да |
| 2 | ответ на задачу, выданную репетитором в чате (экземпляр известен) | 0.8 | да |
| 3 | чат: верно применил / объяснил | 0.5 | нет |
| 3 | чат: «не понимаю», «почему так» | 0.6 как incorrect | нет |
| 3 | чат: вопрос по навыку | 0.2 как incorrect | нет |
| 3 | самооценка в анкете | 0.1 | нет |
| — | пропуск, таймаут | 0 | событие только для темпа |

&nbsp;

Модификаторы: `seen_template_factor` (повтор шаблона) × 0.8; неверный ответ без совпадения с дистрактором × 0.7 по навыку и без свидетельства по заблуждению; частичный зачёт — по доле.

&nbsp;

Три правила, которые не дают чату один тянуть модель:

&nbsp;

1. **Закрыть навык нельзя одним чатом.** `has_strong` обязателен (§4.5).  
2. **Подтвердить заблуждение нельзя одним чатом.** `confirmed` требует `strong_count ≥ 1` (§5.1).  
3. **Чат поднимает `p` не выше потолка.** Ярус 3 не поднимает `p_at_obs` выше `p_chat_cap`. Репликами можно стать «скорее умею», «уверенно» — только задачей.

### 4.4 Цель

Целевой балл экзамена — максимум порогов среди сохранённых программ (ученик может переопределить). Из него — единый `p_target` на экзамен:

&nbsp;

Σ\_i weight\_i · p\_target \= target\_raw\_score   →   p\_target \= target\_raw\_score / max\_raw\_score, потолок p\_target\_max

&nbsp;

Единая цель для всех навыков экзамена — чтобы объяснялась одной фразой: «для 720 нужно держать каждый навык примерно на 90%». Приоритет между навыками — через вес в очереди сетов (§10.1), не через разные цели.

### 4.5 Закрыт / разрыв / повторение

- **Разрыв**: `gap = max(0, p_target − p_recall(now))`.  
- **Навык закрыт** (для данного экзамена): `p_recall ≥ p_target` и `confidence ≥ c_close` и `has_strong = true`.  
- **Мало данных**: `confidence < c_vis` — навык показывается только с этой пометкой, в контекст репетитора идёт как «мало данных», в прогноз не входит.  
- **Повторение** — не отдельный SRS: закрытый навык снова получает `gap > 0`, когда `p_recall` опустится ниже цели, и сборщик сетов подхватывает его как пункт повторения.

### 4.6 Общие навыки двух экзаменов

У навыка с двумя рёбрами `HAS_SKILL` — два `KnowledgeState`, по одному на экзамен. Свидетельство с `exam_id = X` обновляет состояние X с полным весом и состояние второго экзамена с весом `× transfer_cross_exam`, **не устанавливая `has_strong`** для второго. Так работа над SAT подтягивает ЕНТ, но закрыть навык для ЕНТ можно только свидетельством формата ЕНТ. Заблуждения общие (ловушка мышления не зависит от формата); формат-специфичные помечены `exam_specific` и в контекст другого экзамена не идут. Для ученика: «работа над SAT засчитывается в ЕНТ на 60%».

### 4.7 Прогнозный балл и покрытие

predicted\_raw(exam) \= Σ\_i weight\_i · p\_recall\_i          по навыкам с confidence ≥ c\_vis;

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;для остальных — p из приора (§4.8) с пометкой

&nbsp;

coverage(exam)      \= Σ weight\_i · \[confidence\_i ≥ c\_vis\] / Σ weight\_i

&nbsp;

predicted\_scaled    \= ScaleTable(predicted\_raw), пометка «оценочно» для SAT

&nbsp;

В оценку реалистичности подбора (product-logic §3.3) прогноз идёт только при `coverage ≥ c_cov`; иначе — самооценка с пометкой «по твоей оценке». Перед каждым моком `predicted_raw` пишется в `mock.completed.predicted_before` — из пары (прогноз, факт) считается Brier (§11.3).

&nbsp;

**Прогноз даты готовности** — не HLR, а трудоёмкость: `hours_needed = Σ_i gap_i · effort_h_i`, разделить на часы в неделю из профиля → дата. Пересчитывается при каждом свидетельстве и изменении часов. Сравнивается с тест-датой → «успеваешь / не успеваешь» и варианты по темпу (product-logic §3.6).

### 4.8 Приоры из анкеты

- Самооценка по области («уверенно / средне / слабо») → для всех навыков области: `Evidence{kind:'self_report', tier:3, weight:0.1}`; если состояния ещё нет — создать с `h = h₀_prior`, `p_at_obs` \= 0.75 / 0.5 / 0.3, `confidence` \= 0.15.  
- Пробный балл (ЕНТ 28/50, SAT 620\) → распределить по областям пропорционально `score_share` → `p_at_obs` по навыкам области \= доля набранного, `confidence` \= 0.15.  
- Без анкеты и замера — `h = h₀`, `p_at_obs = 0.5`, `confidence = 0`.

&nbsp;

Приоры ниже `c_vis`, поэтому не участвуют в прогнозе и не показываются как знание — только как «по твоей оценке» и как стартовая точка для первого сета.

&nbsp;

---

## 5\. Заблуждения

### 5.1 Статусы и переходы `MisconceptionState`

| Из | В | Условие |
| :---- | :---- | :---- |
| — | `suspected` | первое свидетельство любого яруса |
| `suspected` | `confirmed` | `occurrence_count ≥ 2` из разных событий **и** `strong_count ≥ 1` |
| `confirmed` | `resolved` | `consecutive_avoided ≥ 3` — три подряд задачи/решения, где ловушка была, а ученик не попал; или 1 верный ответ в мини-моке, собранном под это заблуждение (§10.2) |
| `resolved` | `confirmed` | новое попадание — рецидив; `occurrence_count` продолжается, `consecutive_avoided = 0` |
| любой | `disputed` | событие `misconception.disputed` |
| `disputed` | `confirmed` | `strong_count` вырос на 2 после `disputed_at` |
| `disputed` | предыдущий | `misconception.undisputed` |

&nbsp;

«Ловушка была — не попал» фиксируется, когда шаблон отвеченной задачи имеет `TRAPS` на это заблуждение и ответ верный, либо наблюдатель отметил в присланном решении верный шаг там, где ошибка была бы этим заблуждением.

### 5.2 Видимость

| Статус | Ученику | Репетитору (контекст) | Сборщику сетов и задач |
| :---- | :---- | :---- | :---- |
| `suspected` | «подозрение, 1 из 2», раскрываемо | нет | нет |
| `confirmed` | «подтверждено, N наблюдений» | да | да — предпочитать задачи с этой ловушкой |
| `resolved` \< 14 дней | «исправлено, следим» | да, слот `under_watch` | одна проверочная задача с ловушкой в следующем сете |
| `resolved` ≥ 14 дней | в статистике | нет | нет |
| `disputed` | «оспорено» | нет | нет |

### 5.3 Триггеры — при каких условиях проявляется

`triggers` — агрегат по контексту всех свидетельств этого `MisconceptionState`, пересчитывается правилом при каждом обновлении:

&nbsp;

triggers \= {

&nbsp;

&nbsp;&nbsp;by\_task\_type: {mcq4: 3/4, numeric: 1/4},

&nbsp;

&nbsp;&nbsp;by\_difficulty: {"≥4": 3/4},

&nbsp;

&nbsp;&nbsp;hurried: 3/4,            // time\_ratio \< 0.7

&nbsp;

&nbsp;&nbsp;late\_session: 2/4,       // session\_minute \> 30

&nbsp;

&nbsp;&nbsp;after\_guideline: 1/4,

&nbsp;

&nbsp;&nbsp;by\_tag: {negative\_branch: 4/4, sum\_of\_roots: 2/4},

&nbsp;

&nbsp;&nbsp;n: 4

&nbsp;

}

&nbsp;

В контекст репетитора триггер идёт словами и только при `n ≥ 3` и доле `≥ 0.75`: «обычно — на задачах с отрицательной ветвью и когда торопится». Репетитор упоминает триггер только если условие совпало сейчас (§9.4).

### 5.4 Персональные заблуждения

Возникают только из наблюдателя (`proposed_misconception`, §8.1). Канонизация — правилом с точечным вызовом модели:

&nbsp;

1\. embedding(name \+ description)

&nbsp;

2\. top-5 по misc\_emb среди библиотечных того же навыка (+ уже существующие персональные этого ученика)

&nbsp;

3\. similarity \> 0.90            → заменить на существующий id

&nbsp;

&nbsp;&nbsp;&nbsp;0.80 – 0.90                  → один вызов модели: «это одно и то же заблуждение?» (да/нет)

&nbsp;

&nbsp;&nbsp;&nbsp;\< 0.80                       → CREATE (:Misconception {scope:'personal', student\_id}), событие misconception.personal\_created

&nbsp;

У персонального заблуждения нет размеченных дистракторов в шаблонах, поэтому `strong_count` для него растёт только от решений в чате (ярус 2). Переходы — общие (§5.1).

&nbsp;

---

## 6\. Корни ошибок — `ROOT_CAUSE`

Ребро от свидетельства об ошибке в навыке X к навыку Y, из\-за которого ошибка произошла. Карта `REQUIRES` — общая для всех; `ROOT_CAUSE` — персональная: у одного ученика ошибка в тригонометрии уходит в окружность, у другого — в алгебру.

&nbsp;

Три источника:

&nbsp;

| source | Условие | confidence |
| :---- | :---- | :---- |
| `diagnostic` | в замере ошибка в X, затем ошибка в предпосылке Y | 0.8 |
| `observer` | в чате репетитор или ученик назвал корень в Y, ученик не возразил (наблюдение `root_hint`) | 0.6 |
| `rule` | ошибка в X при состоянии предпосылки Y с `p < 0.5` и `confidence > 0.5` | 0.4 |

&nbsp;

Чтение: сборщик сетов поднимает навык Y, если на него ведут `ROOT_CAUSE` за последние 30 дней с суммарной уверенностью ≥ 1.0; контекст репетитора в `prerequisite_gaps` ставит первыми предпосылки с корнями; замер начинает спуск с известных корней.

&nbsp;

---

## 7\. Персональные узлы навыков

**Определение.** Персональный узел — канонический навык, суженный под ученика фильтром по шаблонам: `task_filter = {tags: [...], difficulty?: [..]}`. Создаётся только если фильтр даёт достаточно шаблонов родителя (`min_templates_personal`), иначе узел без задач не накапливал бы свидетельств и не влиял бы ни на что — это нарушает условие существования из product-logic §5.2.

&nbsp;

**Создание** — при `set.opened` (§8.7): модель предлагает, правило проверяет и создаёт.

&nbsp;

**Жизнь.** Задачи для узла — шаблоны родителя по фильтру. Свидетельство крепится к узлу и **пробрасывается на родителя** с весом 1.0 (родитель узнаёт то же, что узел). Состояние узла своё; в прогноз балла входит через родителя (вес наследуется, не суммируется). Показывается только внутри сета и в модели знаний. Живёт, пока есть свидетельства; между учениками не объединяется.

&nbsp;

**Что не становится узлом** — то, что объясняется за минуту: определение, формула, разовое «не понял условие». Это ответ в чате и, при повторе, заблуждение под существующим узлом.

&nbsp;

---

## 8\. Пути записи

Три типа записи по стоимости:

&nbsp;

- **R** — правило, синхронно, в транзакции события. Миллисекунды, детерминировано, повторяемо.  
- **L** — языковая модель, асинхронно, в фоне. Вызов модели \+ риск ложных данных; результат всегда сначала становится событием, потом применяется правилом R.  
- **O** — один раз при загрузке данных.

&nbsp;

| Что | Тип | Триггер |
| :---- | :---- | :---- |
| `events` | R | любое действие |
| канонический слой, шаблоны, `TESTS`/`TRAPS`, эмбеддинги библиотеки заблуждений | O | загрузка данных |
| свидетельства из задач, моков, замера \+ состояния \+ статусы \+ корни \+ очередь | R | `task.answered` |
| приоры | R | `profile.updated` |
| наблюдения из чата | L → событие → R | N сообщений / переход топика / закрытие сета / кнопка |
| персональное заблуждение | R с точечным L | наблюдение `proposed_misconception` |
| персональный узел | L → событие → R | `set.opened` |
| агрегаты профиля | R | раз в сутки, открытие Quack |
| тексты (гайдлайны, объяснения, отчёт по сету) | L | `set.opened`, `set.completed`; в кэш Postgres, не в граф |

&nbsp;

Общий инвариант: **идемпотентность по `event_id`**. `MERGE (e:Evidence {event_id, skill_id})` — повторное применение события не создаёт дублей и не удваивает счётчики. Это условие replay (§8.8).

### 8.1 Чат подготовки — наблюдатель (L → R)

**В момент сообщения.** Пишется `message.user`; контекст топика уже есть (§9); репетитор отвечает; пишется `message.assistant` с разметкой `{mode, gave_task_instance_id?, hint_level?, referenced_skill_ids[]}`. Граф не трогается. Если репетитор выдал задачу в разговоре — `task.issued`, и ответ ученика на неё наблюдатель свяжет с экземпляром.

&nbsp;

**Триггеры наблюдателя.**

&nbsp;

- каждые `observer_every_n` непроцессированных `message.*` в чате;  
- `topic.completed` — переход к следующему топику (обязательный: закрывает топик);  
- `set.completed`;  
- `observer.requested` — ручная кнопка «обновить модель знаний». Кнопка обязана показать, что изменилось; иначе она бессмысленна.

&nbsp;

Эвристики вида «в сообщении есть решение» не нужны: весь контекст в чате, репетитор видит ошибку из истории, а в модель она попадёт на ближайшем триггере.

&nbsp;

**Вход наблюдателя.**

&nbsp;

1. Окно непроцессированных сообщений чата (user и assistant с разметкой).  
2. Срез модели по топику: навык топика, его предпосылки (1–2 хопа) — id, названия, описания, состояние словами.  
3. Заблуждения по этим навыкам: библиотечные и персональные — id, название, описание, статус ученика.  
4. Если в окне есть `task.issued` — экземпляр с разметкой.  
5. `Summary` предыдущего сета (если есть) — для связности.

&nbsp;

**Выход** — structured output:

&nbsp;

{

&nbsp;

&nbsp;&nbsp;"observations": \[

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "solution\_step", "outcome": "incorrect", "skill\_id": "sat.alg.abs\_value\_eq",

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"misconception\_id": "lib.abs\_single\_branch",

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"summary": "рассмотрел только ветвь 2x−6=4, второй ветви не увидел",

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"event\_ids": \[4420\], "confidence": 0.9},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "solution\_step", "outcome": "correct", "skill\_id": "sat.alg.linear\_eq",

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"summary": "верно решил 2x−6=4", "event\_ids": \[4420\], "confidence": 0.95},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "task\_in\_chat", "outcome": "incorrect", "instance\_id": "ti\_88123", "answer": "A",

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"event\_ids": \[4426\], "confidence": 1.0},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "applied", "skill\_id": "…", "summary": "…", "event\_ids": \[4422\], "confidence": 0.8},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "confusion", "skill\_id": "…", "summary": "…", "event\_ids": \[4420\], "confidence": 0.85},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "question", "skill\_id": "…", "summary": "…", "event\_ids": \[4420\], "confidence": 0.8},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "avoided\_trap", "skill\_id": "…", "misconception\_id": "…", "summary": "раскрыл обе ветви модуля", "event\_ids": \[4430\], "confidence": 0.85},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "root\_hint", "skill\_id": "sat.alg.abs\_value\_eq", "root\_skill\_id": "sat.alg.linear\_ineq",

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"summary": "репетитор указал на неравенство, ученик согласился", "event\_ids": \[4421, 4422\], "confidence": 0.7},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "proposed\_misconception", "skill\_id": "…", "name": "…", "description": "…", "error\_class": "conceptual",

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"event\_ids": \[4420\], "confidence": 0.7},

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;{"kind": "pace\_signal", "signal": "asked\_to\_slow\_down", "event\_ids": \[4423\]}

&nbsp;

&nbsp;&nbsp;\]

&nbsp;

}

&nbsp;

Виды и как они применяются:

&nbsp;

| kind | Ярус / вес | Что создаётся |
| :---- | :---- | :---- |
| `solution_step` | 2 / 0.7 | `Evidence` по навыку; при `misconception_id` — и по заблуждению |
| `task_in_chat` | 2 / 0.8, разметка из экземпляра | как `task.answered` (§8.2) |
| `applied` | 3 / 0.5 correct | `Evidence` по навыку |
| `confusion` | 3 / 0.6 incorrect | `Evidence` по навыку |
| `question` | 3 / 0.2 incorrect | `Evidence` по навыку |
| `avoided_trap` | 2 / 0.7 correct | `Evidence` \+ `consecutive_avoided += 1` |
| `root_hint` | — | `ROOT_CAUSE {0.6, 'observer'}` от ближайшего incorrect-свидетельства по этому навыку |
| `proposed_misconception` | — | канонизация §5.4 |
| `pace_signal` | — | в агрегаты профиля |

&nbsp;

**Правила промпту** (жёстко): одно наблюдение — один факт, один `kind`; только существующие id навыков (`proposed_skill` запрещён — навыки фиксированы); `existing` заблуждение предпочтительнее `proposed`; присланное решение разбирать **по шагам** — одно верно решённое уравнение даёт 3–5 свидетельств по разным навыкам, а не одно «решил»; не выводить состояний («слаб в X») — только факты; при сомнении низкий `confidence`, а не пропуск — фильтрует правило; модель дешёвого класса; промпт версионируется, `extractor_version` пишется в событие и в каждый `Evidence`.

&nbsp;

**Запись.** Выход целиком → событие `observation.extracted {payload, extractor_version, source_event_ids}`. Затем правилом: наблюдения с `confidence ≥ observer_min_confidence` → `Evidence` с контекстом (`session_minute`, `topic_skill_id`, `session_id`, `hint_level_before` из разметки репетитора) → HLR (с потолком `p_chat_cap` для яруса 3\) → статусы (`confirmed` только при `strong_count ≥ 1`) → триггеры → корни → очередь и прогноз → контекст топика пересобран. Ученику — «модель знаний обновлена», раскрываемо до сообщения.

&nbsp;

**Почему выход — событие, а не запись в граф.** Replay не требует модели — наблюдения уже лежат. Ложное наблюдение откатывается удалением одного события и пересборкой. Смена промпта — новые события с новым `extractor_version` поверх старых.

### 8.2 Задачи (R)

`task.answered {instance_id, answer, time_spent_sec, mode, session_minute, after_guideline, hint_level_before}` — одна транзакция:

&nbsp;

1. Записать событие → `event_id`.  
2. Прочитать экземпляр: ответ → `correct` / дистрактор с `misconception_id` / без совпадения; для `numeric` — сравнение с `answer_forms` и `trap_answers`; для `multi_select` — доля верных, невыбранные верные → `omission_traps`.  
3. Вес по ярусу и режиму (§4.3), модификаторы (`seen_template`, без совпадения ×0.7).  
4. Создать `Evidence` с контекстом: `task_type, difficulty, tags` (с шаблона), `mode, time_ratio = time_spent / time_reference, session_minute, after_guideline, hint_level_before, exam_id`.  
5. Обновить `KnowledgeState` (новый узел, старый в `PREVIOUS`); для общего навыка — второе состояние с `transfer_cross_exam`.  
6. Обновить `MisconceptionState`: попадание → `occurrence_count`, `strong_count`, переход; верный ответ при наличии `TRAPS` на confirmed-заблуждение → `consecutive_avoided`.  
7. Пересчитать `triggers`.  
8. Правило корня: если ошибка и есть предпосылка с `p < 0.5, conf > 0.5` → `ROOT_CAUSE {0.4, 'rule'}`.  
9. `seen_templates` \+= 1\.  
10. Пересобрать очередь сета и прогноз (§10.1).  
11. Вернуть: результат, решение из экземпляра, новое состояние словами, изменение статуса заблуждения, если было.

&nbsp;

Пропуск и таймаут — событие без свидетельства; таймаут — сигнал темпа.

### 8.3 Моки (R)

Мок — серия `task.answered` с `mode: mock_set | mock_topic | mock_misconception` (вес 1.0) плюс `mock.started` (фиксирует `predicted_before`) и `mock.completed` (сырой балл по правилам секции `ExamFormat`, оценочный шкальный по `ScaleTable`). Сборка мока — §10.2.

### 8.4 Замер (R с очередью)

Цель — не «слабые темы», а фундамент: с какого уровня ученик уверен.

&nbsp;

- **Бюджет**: `diag_base` задач по областям пропорционально `score_share` (ширина) \+ `diag_reserve` задач на спуск (глубина); потолок `diag_max`. Для защиты сжимается пропорционально.  
- **Ход**: каждый ответ — §8.2 с `mode: diagnostic`, вес 1.0. Верно → навык «твёрдо», предпосылкам — косвенное свидетельство `weight 0.3` (чтобы не спускаться зря). Неверно → решение о спуске: резервная задача тратится на самую сильную по `REQUIRES.strength` предпосылку, начиная с навыков, у которых уже есть `ROOT_CAUSE`; приоритет — ошибка в навыке с наибольшим `weight`. Неверно и на предпосылке → `ROOT_CAUSE {0.8, 'diagnostic'}` и спуск ещё на уровень, пока есть резерв. Попадание в ловушку → через 3–4 задачи повторная задача с тем же `TRAPS`.  
- **Прерывание**: очередь спуска и остаток бюджета — в `diagnostic.progress`; «продолжить позже» восстанавливает.  
- **Итог** (`diagnostic.completed`): навыки «твёрдо / шатко», корни, заблуждения `suspected`, уровень, с которого строить. Сеты пересобираются от корней.  
- Замер необязателен: без него первый сет строится по приорам, а предпосылки с «мало данных» проверяются короткими сериями внутри сетов (§10.1).

### 8.5 Анкета (R)

`profile.updated` → приоры (§4.8). Часы в неделю, глубина объяснений, уровень подсказки — читаются из профиля напрямую при сборке контекста и прогноза.

### 8.6 Персональные заблуждения — §5.4.

### 8.7 Персональные узлы (L → R) при `set.opened`

Вход модели: навыки сета с состояниями; `ROOT_CAUSE` за 30 дней; `triggers` confirmed-заблуждений по этим навыкам; доступные `tags` шаблонов этих навыков с количеством шаблонов на тег. Выход: `{"create": [{"parent_skill_id", "name", "description", "task_filter", "reason"}]}` или пусто. Правило: создать, если фильтр даёт `≥ min_templates_personal` шаблонов с `n_seen = 0` у ученика; событие `skill.personal_created`; узел с `PART_OF`; топик в сете получает подзаголовок. Модель не выдумывает подтемы из воздуха — она выбирает фильтр по тому, что уже проявилось.

### 8.8 Replay

rebuild(student\_id):

&nbsp;

&nbsp;&nbsp;1\. снапшот персонального слоя (для сравнения метрик)

&nbsp;

&nbsp;&nbsp;2\. удалить KnowledgeState, MisconceptionState, Evidence, ROOT\_CAUSE, персональные Skill/Misconception этого ученика

&nbsp;

&nbsp;&nbsp;3\. прогнать events по occurred\_at:

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;task.answered / profile.updated / misconception.disputed / skill.personal\_created …  — правилом

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;observation.extracted — правилом; при нескольких версиях по одним source\_event\_ids — последняя

&nbsp;

&nbsp;&nbsp;4\. сравнить Brier и число confirmed до/после; при деградации — откат

&nbsp;

Модель не участвует. Замена версии наблюдателя — отдельная фоновая задача, которая создаёт новые `observation.extracted` по старым сообщениям; после неё — replay.

&nbsp;

---

## 9\. Контекст репетитора

### 9.1 Два уровня

**Контекст топика** — собирается при `topic.opened`, хранится как документ (кэш), пересобирается по событиям: наблюдатель записал наблюдения; состояние навыка топика изменилось от задачи; `topic.completed` → сборка для следующего топика. Не собирается на каждое сообщение.

&nbsp;

**Строка сессии** — на каждое сообщение: минута сессии, результат последней задачи, режим последнего сообщения ученика, окно последних `chat_window` сообщений.

&nbsp;

Чат на уровне сета (поверх топиков) получает контекст сета: те же слоты по всем навыкам сета с лимитами ×1.5.

### 9.2 Слоты контекста топика

Собираются 4 параллельными Cypher-запросами. Порядок слотов — порядок в блоке; заблуждения не первые.

&nbsp;

| Слот | Лимит | Источник и правило |
| :---- | :---- | :---- |
| `topic` | 1 | навык топика: p, conf, тренд по последним 3 состояниям, `due`; место в сете («2 из 3, дальше — формулы приведения»); дедлайн сета |
| `strengths` | 2 | навыки топика и предпосылок с `p ≥ 0.8, conf ≥ 0.5` — чтобы репетитор опирался на то, что ученик умеет |
| `prerequisite_gaps` | 3 | предпосылки (1–2 хопа) с `p < 0.6, conf > 0.5`; первыми — с `ROOT_CAUSE` этого ученика |
| `active_misconceptions` | 2 | `confirmed`, `ABOUT` навык топика или его предпосылки (не все заблуждения ученика); с триггерами словами при `n ≥ 3` |
| `under_watch` | 1 | `resolved` \< 14 дней по тем же навыкам |
| `low_data` | 2 | навыки топика/предпосылок с `conf < c_vis` — как «мало данных», не как слабые |
| `deadline` | 2 | дедлайн сета, ближайшая тест-дата |
| `profile` | 3 строки | уровень подсказки, глубина объяснений, часов в неделю, темп |
| `previous_set` | 1 | `Summary` предыдущего сета, 2–3 предложения |

&nbsp;

Пустой слот лучше нерелевантного: навык с `p = 0.93` в слоте «слабые» заставит модель «лечить» здоровое.

### 9.3 Формат инъекции

Структурированный блок в system prompt после роли и перед окном диалога; не проза.

&nbsp;

\<learner\_model topic="Раскрытие модуля" set="Сет 2 · 2 из 3 · до 5 окт" as\_of="2026-09-17T14:02"\>

&nbsp;

topic: раскрытие модуля — p=0.55 conf=0.8 trend=flat; дальше в сете: формулы приведения

&nbsp;

strengths:

&nbsp;

&nbsp;&nbsp;\- линейные уравнения: p=0.88 conf=0.9

&nbsp;

&nbsp;&nbsp;\- разложение на множители: p=0.82 conf=0.7

&nbsp;

prerequisite\_gaps:

&nbsp;

&nbsp;&nbsp;\- линейные неравенства: p=0.42 conf=0.6 (корень 2 ошибок в этом навыке за 30 дней)

&nbsp;

active\_misconceptions:

&nbsp;

&nbsp;&nbsp;\- теряет вторую ветвь при |x−a| (подтверждено, 3 набл.; обычно — при отрицательной ветви и когда торопится)

&nbsp;

under\_watch: \[\]

&nbsp;

low\_data:

&nbsp;

&nbsp;&nbsp;\- формулы приведения: мало данных

&nbsp;

deadline: сет до 5 окт; SAT 7 ноя

&nbsp;

profile: подсказка уровня 1 обычно достаточна; объяснения standard; \~4 ч/нед

&nbsp;

previous\_set: закрыл квадратичные и системы; знак при раскрытии скобок исправлен

&nbsp;

policy: (§9.4)

&nbsp;

\</learner\_model\>

### 9.4 Политика поведения

Строки `policy` — реализация «репетитор знает, но не охотится»:

&nbsp;

- **Режим по последнему сообщению ученика.** Вопрос или просьба объяснить → режим «объясняю»: заблуждения не упоминаются, не проверяются, не подводятся. Присланное решение или ошибка в задаче → режим «разбираю»: заблуждения и корни включаются.  
- Заблуждения — для интерпретации ошибок, когда они случаются. Не тема разговора, не повод для проверки, не начало ответа.  
- Не упоминать заблуждение, пока не наблюдаешь повтор в этой сессии.  
- Триггер упоминать только если условие совпало сейчас («ты обычно торопишься на таких — сейчас 40 секунд из 75»).  
- Подсказки — с уровня из профиля; выше — по запросу или после второй неудачи.  
- При ошибке, корень которой в `prerequisite_gaps`, — назвать корень и предложить отступить; не настаивать.  
- Опираться на `strengths`: объяснять новое через то, что ученик умеет.  
- Навыки из `low_data` — не называть слабыми.  
- Можно дать одну задачу в разговоре, если естественно; не превращать чат в допрос.  
- Требования, даты, стоимость, правила поступления — не зона репетитора; отправлять в подбор. Правила и формат экзамена — только через `get_exam_format`.

### 9.5 Инструменты репетитора (только чтение)

- `explain_belief(node_id)` — раскрыть `Skill` / `Misconception` до списка `Evidence` с `event_id`, текстом задачи и ответом ученика или фрагментом сообщения. По запросу ученика «почему ты так считаешь».  
- `get_task(skill_id, with_trap?: misconception_id, exclude_seen: true)` — экземпляр из пула в разговор; пишет `task.issued`.  
- `get_exam_format(exam_id)` — факты из §2.3 с источниками.  
- `get_learner_context(...)` — вызывается **фреймворком**, не моделью.

&nbsp;

Инструментов записи у репетитора нет.

&nbsp;

---

## 10\. Потребители модели знаний

### 10.1 Сборщик сетов `[B1]`

Правила, без модели. Пересборка — после каждого свидетельства и любого изменения входов (часы, тест-дата, цель, сохранённые, ручная смена).

&nbsp;

для каждого навыка экзамена:

&nbsp;

&nbsp;&nbsp;gap      \= max(0, p\_target − p\_recall)

&nbsp;

&nbsp;&nbsp;urgency  \= 1 \+ max(0, (60 − days\_to\_test) / 60\)

&nbsp;

&nbsp;&nbsp;root\_boost \= 1.5, если на навык ведут ROOT\_CAUSE за 30 дней с Σ confidence ≥ 1.0, иначе 1.0

&nbsp;

&nbsp;&nbsp;need     \= weight · gap · urgency · root\_boost

&nbsp;

Очередь: сортировка по `need`; **предпосылка с `gap > 0` и `conf ≥ c_vis` — раньше зависящего навыка** (топологический порядок по `REQUIRES`); предпосылка с `conf < c_vis` входит в сет как **короткая проверка** (2–3 задачи, не топик). Сет — голова очереди размером `set_size`; персональные узлы — внутри топика родителя. Дедлайн сета — `Σ gap_i · effort_h_i / hours_per_week`, не позже ближайшей тест-даты. `resolved < 14д` — одна проверочная задача с ловушкой. Последний сет перед тестом — закрепление без новых навыков. Ручная смена уважается: незакрытые навыки сменённого сета остаются в своём состоянии и вернутся через `gap`.

### 10.2 Выбор задачи и сборка моков `[B1]`

Одна задача: шаблон навыка (или по `task_filter` персонального узла), `n_seen = 0` предпочтительно; сложность — на шаг выше последней верной, на шаг ниже после двух неверных; при `confirmed`\-заблуждении по навыку — предпочтительно шаблон с `TRAPS` на него; для проверки `resolved` — шаблон **другой** структуры с той же ловушкой. Экземпляр генерируется по seed.

&nbsp;

Моки — один сборщик, три вида, все по `Section` из `ExamFormat`:

&nbsp;

- **по сету** — навыки сета, 8–12 заданий, доли типов и сложности как в секции, время пропорционально;  
- **по топику** — 5–7 заданий одного навыка;  
- **под заблуждение** — 2–3 задания с `TRAPS` на него; верный ответ → `resolved`. Полный мок с адаптивным модулем — стретч.

&nbsp;

Подсчёт — по `scoring_rule` секции; SAT — шкала «оценочно».

### 10.3 Прогнозный балл и реалистичность `[B1 → B2]`

§4.7. Подбор читает только агрегат: `{exam_id, predicted_raw, predicted_scaled, coverage, as_of, last_change}`. Кэш по последнему `event_id` ученика.

### 10.4 Отчёт по сету `[B2]`

При `set.completed`:

&nbsp;

1. **Статистика правилом**: задач решено / верно; навыков закрыто из скольких; заблуждений `resolved` за сет; дней в сете против дедлайна («на 2 дня раньше»); навыки, состояние которых выросло сильнее всего (по `PREVIOUS` на `set.opened` и сейчас); прогноз готовности до/после.  
2. **Текст моделью**: короткий, приободряющий, из статистики — что усвоил, что стало увереннее, что следим. Один вызов.  
3. Хранится как `Summary{scope:'set', set_id, text, stats}` в Postgres; идёт в слот `previous_set` контекста первого топика следующего сета.

&nbsp;

Summary по топику отдельно не нужен — контекст топика пересобирается из графа, наблюдатель на переходе отрабатывает.

### 10.5 «Почему так считаешь» `[F2]`

Любое утверждение ученику — ссылка: `MisconceptionState / KnowledgeState → Evidence → event_id → экземпляр задачи с ответом или фрагмент сообщения`. Одно действие «не согласен» на заблуждении → `misconception.disputed`.

### 10.6 Ассистент подбора `[B2]`

В подбор модель знаний идёт только агрегатом §10.3 плюс diff с прошлой сессии («после замера две программы стали „реалистично“»). Инструменты: `update_profile`, `run_matching`, `compare`, `save_program`, `get_program_facts`, `get_admission_route`, `get_exam_format`, `query_dataset`. Факты — только из инструментов; постпроверка выхода: число или дата без источника в результате инструмента — ответ помечается и не выдаётся.

### 10.7 Профиль ученика (procedural)

Раз в сутки и при открытии Quack: `hours_per_week_actual` (по сессиям в `events`), `active_days`, `error_class_dist` (по `MisconceptionState` с `occurrence_count`), `pace_signals` (таймауты, `asked_to_slow_down`). Читается контекстом (§9.2 `profile`) и Quack (темп «заявлено / фактически»). Циклы интервенций (что помогло) не строятся.

&nbsp;

---

## 11\. Честность, качество, отказы

### 11.1 Честность

- Провенанс у каждого утверждения (§10.5).  
- `suspected` не в контекст; `confirmed` — только с сильным свидетельством; `disputed` — нигде до двух новых сильных.  
- Навык с `conf < c_vis` — «мало данных», не «слабый».  
- Прогноз в реалистичности — только при `coverage ≥ c_cov`; иначе «по твоей оценке».  
- SAT-шкала — «оценочно»; экземпляры задач — «сгенерировано из проверенного шаблона»; ручные — «проверено руками».  
- Процентов шансов нет нигде: схема выхода ассистента и репетитора не содержит поля для них, постпроверка режет.

### 11.2 Главный риск — ложное наблюдение

Ложное заблуждение в графе хуже отсутствия памяти: репетитор начнёт «лечить» то, чего нет, и доверие сломается на первом «нет, я не путаю». Страховки, по слоям: порог `observer_min_confidence`; ярус 3 не закрывает и не подтверждает; потолок `p_chat_cap`; `confirmed` требует `strong_count ≥ 1`; в контекст — не более двух заблуждений и только по навыкам топика; диспут одним действием; replay по событиям.

### 11.3 Метрики

| Метрика | Как | Зачем |
| :---- | :---- | :---- |
| Brier | `mean((predicted_before/max − raw/max)²)` по мокам | калибровка модели забывания; считается с первого мока, показывается на защите как «механизм есть, данных мало» |
| доля `confirmed`, перешедших в `resolved` | по `MisconceptionState` | продукт учит, а не только диагностирует |
| точность наблюдателя | 20–30 размеченных фрагментов чата → precision/recall по (kind, skill) | гейт перед сменой `extractor_version` `[OPEN: стретч]` |
| доля диспутов | `disputed / confirmed` | сигнал ложных наблюдений |

### 11.4 Отказы

| Недоступно | Работает | Что показывается |
| :---- | :---- | :---- |
| языковая модель | задачи, моки, замер, состояния, статусы, сеты, прогноз, реалистичность, сравнение, вехи | один статус «ассистент временно недоступен»; чаты выключены; гайдлайны и объяснения — из кэша с пометкой «сохранённая версия»; наблюдения — очередь, применятся при восстановлении |
| Neo4j | события пишутся; профиль, сохранённые, вехи, кэш программ | сеты — статический порядок канонической карты с пометкой; ответы на задачи копятся как события и применяются при восстановлении; прогноз «недоступен» |
| Postgres | — | продукт недоступен (source of truth) |
| эмбеддинги | всё, кроме канонизации персональных заблуждений | `proposed_misconception` ждёт в очереди |

&nbsp;

Пустых экранов нет: нечего показать — объяснение и следующее действие.

&nbsp;

---

## 12\. Конфиг — все параметры в одном месте

Значения — стартовые, из HLR-литературы и здравого смысла; калибровки на хакатоне не будет. Изменение — без изменения кода.

&nbsp;

| Параметр | Значение | Где используется |
| :---- | :---- | :---- |
| `alpha` | 1.0 | §4.1 рост h при верном |
| `beta` | 0.5 | §4.1 падение h при неверном |
| `h0` | 24 ч | §4.1 старт без приора |
| `h0_prior` | 240 ч | §4.8 старт при самооценке «уверенно» |
| `h_min` / `h_max` | 12 ч / 8760 ч | §4.1 |
| `k_confidence` | 3.0 | §4.2 |
| `p_chat_cap` | 0.8 | §4.3 потолок для яруса 3 |
| `p_target_max` | 0.95 | §4.4 |
| `c_vis` | 0.3 | §4.5 «мало данных» |
| `c_close` | 0.6 | §4.5 закрытие навыка |
| `c_cov` | 0.6 | §4.7 покрытие для реалистичности |
| `transfer_cross_exam` | 0.6 | §4.6 |
| `seen_template_factor` | 0.8 | §3.6 |
| `unmatched_incorrect_factor` | 0.7 | §8.2 |
| `prior_indirect_weight` | 0.3 | §8.4 косвенное свидетельство предпосылкам при верном в замере |
| `misc_confirm_min_occ` | 2 | §5.1 |
| `misc_resolve_avoided` | 3 | §5.1 |
| `under_watch_days` | 14 | §5.2 |
| `trigger_min_n` / `trigger_min_share` | 3 / 0.75 | §5.3 |
| `root_window_days` / `root_boost` | 30 / 1.5 | §6, §10.1 |
| `canon_merge` / `canon_adjudicate` | 0.90 / 0.80 | §5.4 |
| `min_templates_personal` | 3 | §7 |
| `observer_every_n` | 6 | §8.1 |
| `observer_min_confidence` | 0.7 | §8.1 |
| `diag_base` / `diag_reserve` / `diag_max` | 8 / 4 / 12 | §8.4 |
| `set_size` | 3 топика | §10.1 |
| `chat_window` | 10 сообщений | §9.1 |
| `context_budget_tokens` | 3000 | §9.2 |

&nbsp;

---

## 13\. Открытые вопросы

1. Объём шаблонов на навык и число ручных задач с рисунками `[B2]`.  
2. Фактическое пересечение карт SAT / ЕНТ — сколько навыков общих `[B1]`.  
3. Формат шаблона: JSON с выражениями или Python-функция на шаблон. Второе проще проверять, первое — проще редактировать без кода `[B2]`.  
4. Хранить полную цепочку `PREVIOUS` или сэмплировать старше 30 дней — на хакатоне хранить всё.  
5. Eval наблюдателя — стретч; минимум 10 фрагментов вручную перед защитой.  
6. Контекст чата на уровне сета — те же слоты ×1.5 или отдельная сборка.  
7. Что показывает кнопка «обновить модель знаний», когда наблюдатель ничего не нашёл.

&nbsp;

---

## Приложение А. Соответствие с `memory-architecture.md` (исходный документ)

| Взято как есть | Адаптировано | Не взято |
| :---- | :---- | :---- |
| события — source of truth, граф — projection; replay | навыки: фиксированная каноническая карта вместо LLM-извлечения и канонизации | `Topic` / `Subject`; `Deadline` как узел графа (в Quack — вехи в Postgres) |
| `Skill / Misconception / Evidence / KnowledgeState` с `PREVIOUS`; HLR с вычислением при чтении; confidence отдельно от p | заблуждение — общий узел \+ персональный `MisconceptionState`; `Evidence` несёт контекст ситуации; `triggers` | материалы, `MaterialChunk -[:TEACHES]->`, нотация лектора; фото и canvas |
| «агент не пишет в граф»; наблюдатель отдельно и асинхронно; structured output с `existing`/`proposed` | выход наблюдателя — событие; два пути записи (правило для задач, наблюдатель для чата); ярусы доверия | конспект как view; карточки; session/topic Summary (только Summary по сету) |
| контекст как структурированный блок с `policy`; бюджет по слотам; «пустой слот лучше нерелевантного» | контекст собирается на топик, не на сообщение; слоты `strengths`, `low_data`, режим по последнему сообщению | семантический слот по вектору свидетельств; эмбеддинги сырых сообщений |
| канонизация по эмбеддингу с LLM-адъюдикацией в серой зоне | только для персональных заблуждений против библиотеки | пакетная канонизация навыков (HDBSCAN) |
| провенанс до события; `disputed`; Brier как метрика; «ложное заблуждение хуже отсутствия памяти» | `ROOT_CAUSE` как персональное ребро; шаблоны задач с размеченными дистракторами вместо mock-генерации под заблуждение | cross-student слой, cohort priors, `LearnerProfile` как узел графа; циклы интервенций |

&nbsp;