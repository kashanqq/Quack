# Формат данных — B1

Quack! · фаза 2 · v2.0 · 18.09.2026

Владелец: **B1**. Читают: B1, B2, B3. Источник: `memory-architecture-quack.md §2–3`, `00-contracts.md §4.1, §6`, `00-contracts-phase2.md §3.6`.

Этот файл описывает **формат** каждого JSON-файла в `data/`. По нему любой участник команды может написать новую запись без вопросов. Валидация — через Pydantic-модели из `app/schemas/knowledge.py`, `app/schemas/tasks.py`.

Общие правила:

- UTF-8, без BOM. Ключи — snake_case, латиницей.
- Все `id` — строки. Стиль id — `00-contracts.md §4.1`.
- Даты — ISO 8601: `YYYY-MM-DD` для дат, `YYYY-MM-DDTHH:MM:SSZ` для datetime.
- Числа — JSON number, не строка.
- Где источник не проверен руками — `"is_demo": true`.
- Порядок ключей не важен, но в примерах показан «правильный» для читаемости.

---

## 1. `data/skills/<exam>.json` — карта навыков

Файлы: `sat_math.json`, `ent_math.json`.

Один навык может принадлежать двум экзаменам (общий, id вида `math.<area3>.<name>`). Такой навык описан **один раз** — в `sat_math.json`, в `ent_math.json` он только ссылка в `areas[].skills` с весом.

### Схема

```json
{
  "exam": {
    "id": "SAT_MATH",
    "name": "SAT Math",
    "max_raw_score": 44
  },
  "areas": [
    {
      "id": "area.sat.algebra",
      "name": "Algebra",
      "score_share": 0.35,
      "skills": [
        { "id": "sat.alg.linear_eq", "weight": 2.5 },
        { "id": "math.alg.quadratic_roots", "weight": 3.0 }
      ]
    }
  ],
  "skills": [
    {
      "id": "sat.alg.linear_eq",
      "name": "Линейные уравнения",
      "description": "Решение уравнений вида ax + b = c с одной переменной; перенос членов, деление на коэффициент.",
      "effort_h": 4,
      "base_half_life_h": null,
      "requires": [
        { "skill_id": "math.arith.fractions", "strength": 0.8 }
      ]
    }
  ],
  "sources": [
    { "url": "https://satsuite.collegeboard.org/sat/whats-on-the-test/math", "checked_at": "2026-09-17" }
  ]
}
```

### Правила

- **Σ weight** по всем `areas[].skills` экзамена == `exam.max_raw_score` (± 1e-6). Проверяется загрузчиком и тестом `tests/seed/test_data_schemas.py`.
- **`requires`** — DAG, без циклов. `strength ∈ (0, 1]`. Проверяется тем же тестом.
- **`score_share`** по экзамену в сумме ≈ 1.0 (доли областей).
- **`effort_h`** — часы на освоение с нуля до цели. Целое или float, > 0.
- **`base_half_life_h`** — либо число, либо `null` (тогда берётся из `settings.KNOWLEDGE.h0`).
- Названия и описания — **на русском**, 1–2 предложения.
- `id` навыков:
  - специфичный для экзамена — `<exam>.<area3>.<name>`, например `sat.alg.linear_eq`, `ent.geo.stereo_volumes`;
  - общий для двух экзаменов — `math.<area3>.<name>`, например `math.alg.quadratic_roots`.
- `id` области: `area.<exam-lower>.<name>`, например `area.sat.algebra`.
- Объём Ф1: SAT Math — 35–45 навыков по 4 областям College Board; ЕНТ математика — 20–25 навыков по спецификации НЦТ.

---

## 2. `data/exam_formats/<exam>.json` — формат экзамена

Файлы: `sat_math.json`, `ent_math.json`.

### Схема

```json
{
  "exam_id": "ENT_MATH",
  "name": "ЕНТ, профильная математика",
  "max_raw_score": 50,
  "sections": [
    {
      "name": "Основной блок",
      "n_items": 35,
      "minutes": 90,
      "item_types": { "mcq5": 25, "multi_select": 10 },
      "scoring_rule": "mcq5: 1 балл за верный; multi_select: 2 балла при всех верных и отсутствии неверных, 1 балл при частично верном без неверных",
      "calculator": false,
      "adaptive": false,
      "area_shares": {
        "area.ent.algebra": 0.4,
        "area.ent.geometry": 0.3,
        "area.ent.functions": 0.3
      },
      "difficulty_shares": { "1": 0.2, "2": 0.3, "3": 0.3, "4": 0.2 },
      "answer_forms": ["integer", "fraction"]
    }
  ],
  "scale_table": null,
  "scale_note": null,
  "source": "https://testcenter.kz",
  "checked_at": "2026-09-17",
  "is_demo": true
}
```

Для SAT:

```json
"scale_table": {
  "30": 480, "35": 530, "40": 580, "44": 620,
  "comment": "оценочная конверсия, College Board не публикует шкалу для Digital SAT"
},
"scale_note": "оценочно"
```

### Правила

- `item_types` — словарь тип→количество; сумма значений == `n_items`.
- `area_shares` — суммы весов == 1.0 (± 1e-6). Ключи — `id` областей из `data/skills/<exam>.json`.
- `scale_table` — **только SAT**, `null` для ЕНТ. Реальные значения по возможности из College Board; иначе `is_demo: true`.
- `is_demo: true` там, где не проверено по официальному источнику.
- `source` — URL официальной спецификации (College Board, testcenter.kz).

---

## 3. `data/misconceptions/<area>.json` — библиотека заблуждений

**Один файл на область.** Загрузчик (`app/seed/misconceptions.py`) читает каталог `data/misconceptions/*.json`, объединяет все записи, проверяет уникальность `id` по всем файлам.

Файлы SAT: `alg.json`, `adv.json`, `psda.json`, `geo.json`.
Файлы ЕНТ: `ent_alg.json`, `ent_num.json`, `ent_func.json`, `ent_trig.json`, `ent_geo.json`, `ent_stereo.json`.

Пустые файлы не создаются — если у области ещё нет своих заблуждений, файла нет.

### Схема (пример `alg.json`)

```json
[
  {
    "id": "lib.abs_single_branch",
    "name": "Раскрытие модуля только в одной ветви",
    "description": "Ученик решает |ax − b| = c как ax − b = c и теряет вторую ветвь ax − b = −c.",
    "error_class": "conceptual",
    "skill_ids": ["math.alg.abs_value_eq"],
    "exam_specific": null
  },
  {
    "id": "lib.vieta_sign_confusion",
    "name": "Путаница знаков в теореме Виета",
    "description": "Ученик считает, что сумма корней равна +b/a, а произведение −c/a, забывая смену знака.",
    "error_class": "conceptual",
    "skill_ids": ["math.alg.quadratic_roots"],
    "exam_specific": null
  }
]
```

### Правила

- `error_class` ∈ `{"computational", "conceptual", "attention", "procedural"}`.
- `skill_ids` — непустой список. Все `id` должны существовать в `data/skills/*.json`.
- `exam_specific` — `null` (общая ловушка) или `ExamId` (ловушка только этого формата).
- **`id` уникален по всему каталогу**, а не только внутри файла. Загрузчик падает, если в `alg.json` и `adv.json` встретится один и тот же `id`.
- **Область записи.** Запись лежит в файле той области, где находится её **первый `skill_id`**. Если первый `skill_id` — общий `math.*` (определён в `sat_math.json`), запись идёт в SAT-область, где этот навык впервые появляется. Ссылки на навыки чужих областей — норма, менять расположение записи из-за них не нужно.
- **Ссылки на чужие заблуждения.** Если шаблон области A хочет использовать заблуждение из файла области B — это разрешено (по `id`), но владелец области A пишет об этом в `docs/sync-log.md`, чтобы владелец B знал.
- `embedding` в файлах **не хранится** — вычисляется при seed через `app/embeddings.py` из `name + description` и пишется в Neo4j.
- **Объём Ф2:** ~15 записей сейчас, расширяется вместе с шаблонами (2–4 заблуждения на область).

---

## 4. `data/templates/**/*.json` — шаблоны задач

Один шаблон = один файл. Структура папок: `data/templates/<exam_lower>/<area3>/<name>.json`.

**Папки по областям:**

- SAT: `data/templates/sat/{alg,adv,psda,geo}/`
- ЕНТ: `data/templates/ent/{ent_alg,ent_num,ent_func,ent_trig,ent_geo,ent_stereo}/`

Пример: `data/templates/sat/alg/abs_eq_sum_roots.json`.

**Квота:** 2–3 шаблона на каждый навык своей области. Целевой объём Ф2 — по 2–3 на навык обоих экзаменов (~120–170 шаблонов), распределение типов и сложности как в `ExamFormat.sections[].item_types` и `difficulty_shares`.

**Покрытие.** Команда `python scripts/seed.py --coverage` печатает таблицу «навык → число шаблонов» и помечает навыки с `< 2` шаблонов. В приёмке фазы 2 — ни одного навыка в своих областях с `< 2`.

**Дистракторы и заблуждения.** Дистрактор ссылается на `misconception_id` из файла **своей области** (`data/misconceptions/<area>.json`). Чужое заблуждение — только через запись в `docs/sync-log.md` владельцу той области.

### Схема — MCQ

```json
{
  "id": "tpl.sat.alg.abs_eq_sum_roots",
  "exam_id": "SAT_MATH",
  "type": "mcq4",
  "difficulty": 3,
  "skill_id": "sat.alg.abs_value_eq",
  "tags": ["negative_branch", "sum_of_roots"],
  "time_reference_sec": 75,
  "kind": "template",
  "params": {
    "a": { "range": [2, 5] },
    "b": { "range": [2, 12] },
    "c": { "range": [1, 9] }
  },
  "constraints": [
    "(b + c) % a == 0",
    "(b - c) % a == 0",
    "b > c"
  ],
  "stem": "|{a}x − {b}| = {c}. Чему равна сумма корней уравнения?",
  "correct": "2*b/a",
  "distractors": [
    { "expr": "(b + c)/a", "misconception_id": "lib.abs_single_branch" },
    { "expr": "(b - c)/a", "misconception_id": "lib.abs_single_branch" },
    { "expr": "-2*b/a", "misconception_id": "lib.abs_sign_drop" },
    { "expr": "2*c/a", "misconception_id": null }
  ],
  "solution": [
    "Раскрыть модуль: {a}x − {b} = {c} или {a}x − {b} = −{c}",
    "x1 = ({b}+{c})/{a}, x2 = ({b}−{c})/{a}",
    "Сумма = 2·{b}/{a} = {answer}"
  ],
  "generator": null,
  "figure": null
}
```

### Схема — numeric

```json
{
  "id": "tpl.sat.arith.percent_change",
  "exam_id": "SAT_MATH",
  "type": "numeric",
  "difficulty": 2,
  "skill_id": "sat.psda.percent",
  "tags": ["percent_change"],
  "time_reference_sec": 60,
  "kind": "template",
  "params": {
    "base": { "range": [50, 500] },
    "pct":  { "range": [5, 40] }
  },
  "constraints": ["base * pct % 100 == 0"],
  "stem": "Число {base} увеличили на {pct}%. Какое число получилось?",
  "correct": "base * (100 + pct) / 100",
  "distractors": [],
  "answer_forms": ["integer", "fraction", "decimal:2"],
  "trap_answers": [
    { "expr": "base * pct / 100", "misconception_id": "lib.percent_of_not_increase" },
    { "expr": "base * (100 - pct) / 100", "misconception_id": null }
  ],
  "solution": [
    "{base} × (1 + {pct}/100)",
    "= {answer}"
  ],
  "generator": null,
  "figure": null
}
```

### Схема — multi_select

```json
{
  "id": "tpl.ent.alg.multi_root_conditions",
  "exam_id": "ENT_MATH",
  "type": "multi_select",
  "difficulty": 4,
  "skill_id": "math.alg.quadratic_roots",
  "tags": ["vieta", "sign"],
  "time_reference_sec": 120,
  "kind": "template",
  "params": {
    "p": { "range": [-5, 5] },
    "q": { "range": [1, 9] }
  },
  "constraints": ["p*p - 4*q > 0"],
  "stem": "Уравнение x² + {p}x + {q} = 0. Выберите все верные утверждения.",
  "correct": ["корни разных знаков", "произведение корней положительно"],
  "distractors": [
    { "expr": "корни одного знака", "misconception_id": null },
    { "expr": "корни равны", "misconception_id": null }
  ],
  "omission_traps": [
    { "omit": "корни разных знаков", "misconception_id": "lib.vieta_sign_confusion" }
  ],
  "solution": ["...", "..."],
  "generator": null,
  "figure": null
}
```

### Схема — manual (задача с рисунком)

```json
{
  "id": "tpl.sat.geo.circle_chord_manual",
  "exam_id": "SAT_MATH",
  "type": "mcq4",
  "difficulty": 4,
  "skill_id": "sat.geo.circle",
  "tags": ["circle", "chord", "figure"],
  "time_reference_sec": 90,
  "kind": "manual",
  "params": {},
  "constraints": [],
  "stem": "В окружности радиусом 5 проведена хорда AB. Расстояние от центра до хорды равно 3. Найдите длину хорды AB. (см. рисунок)",
  "correct": "8",
  "distractors": [
    { "expr": "4", "misconception_id": null },
    { "expr": "6", "misconception_id": null },
    { "expr": "√34", "misconception_id": null }
  ],
  "solution": ["...", "..."],
  "generator": null,
  "figure": "data/templates/sat/geo/figures/circle_chord_01.svg"
}
```

### Правила

- `type` ∈ `{"mcq4", "mcq5", "multi_select", "numeric"}`.
- `kind` ∈ `{"template", "manual"}`. Для `manual`: `params={}`, `constraints=[]`, обязательно `figure`.
- **Имена в формулах** — только из белого списка `app/tasks/evaluate.py: ALLOWED_NAMES` (`sqrt`, `Abs`, `Rational`, `sin`, `cos`, `pi`, `E`, `Min`, `Max`, `gcd`, `lcm`, `factorial`, `log`, `exp`) плюс параметры из `params`. **Никакого eval.** Любое имя вне словаря → `TemplateError`.
- **`correct`**:
  - `mcq4`/`mcq5`/`numeric` — одно выражение-строка;
  - `multi_select` — список строк (все верные).
- **`distractors`**: для `mcq4` — минимум 3, для `mcq5` — 4. `expr` — выражение (mcq) или текст (multi_select). `misconception_id: null` означает «случайный дистрактор, без диагностики».
- **`omission_traps`** — только для `multi_select`.
- **`trap_answers`** — только для `numeric`. 2–3 записи; без них numeric-задача не даёт диагностики.
- **`answer_forms`** — только для `numeric`, список допустимых форматов записи ответа: `integer`, `fraction`, `decimal:<n>` (округление до n знаков).
- **`generator`** — имя функции в `app/tasks/generators.py:GENERATORS`, если шаблон не параметризуется через `params`, а требует специальной логики. Обычно `null`.
- **`figure`** — путь относительно корня репо. Только для `kind="manual"`.
- **`{answer}`** в `solution[*]` подставляется канонической строкой ответа при рендере.
- **Инварианты шаблона** (проверяет `validate_template(spec, n_seeds=50)`):
  1. ровно один верный вариант (mcq4/mcq5) / заявленное множество (multi_select) / одна величина (numeric);
  2. все дистракторы попарно различны и не равны верному;
  3. значения в допустимом диапазоне (целые если `constraints` требуют; без деления на ноль);
  4. решение при подстановке сходится с `correct`;
  5. нет дубля по `(template_id, seed)`.
  Один `TemplateError` на seed ≤ 10% сидов — допустимо. Больше — шаблон отклоняется с ошибкой `seed failure rate`.

---

## 5. `data/knowledge_base/exams.json` — база знаний об экзаменах

Файл-массив узлов `Fact` с `source`.

### Схема

```json
[
  {
    "id": "fact.sat.math.overview",
    "node_id": "SAT_MATH",
    "text": "SAT Math — часть Digital SAT. Два модуля по 22 задания, 35 минут каждый. Второй модуль адаптивный: сложность зависит от результата первого. Калькулятор разрешён во всех модулях.",
    "source": "https://satsuite.collegeboard.org/sat/whats-on-the-test/math",
    "checked_at": "2026-09-17",
    "is_demo": false
  }
]
```

### Правила

- `node_id` — `ExamId` или `country_id` (например `KZ`).
- Один факт = одна мысль. Не смешивать правила и статистику в одном тексте.
- Каждый факт обязан иметь `source` и `checked_at`. Если источник не проверен — `is_demo: true`.

---

## 6. `data/knowledge_base/routes.json` — маршруты поступления по странам

### Схема

```json
[
  {
    "country_id": "KZ",
    "routes": [
      {
        "id": "kz.grant",
        "name": "Государственный грант по ЕНТ",
        "description": "Грант по конкурсу баллов ЕНТ. Профильная пара предметов зависит от специальности.",
        "requirements": [
          {
            "type": "exam_score",
            "exam_id": "ENT_MATH",
            "threshold": 35,
            "comparator": ">=",
            "description": "Проходной балл по профильной математике для IT-специальностей (оценочно).",
            "source": "https://testcenter.kz"
          }
        ],
        "source": "https://testcenter.kz",
        "checked_at": "2026-09-17",
        "is_demo": true
      }
    ]
  }
]
```

### Правила

- `country_id` — ISO alpha-2.
- `type` ∈ `{"exam_score", "language", "gpa", "document", "other"}`.
- `comparator` ∈ `{">=", "<=", "range", "present"}`. Для `range` — `threshold` = список из двух чисел; для `present` — `threshold: null`.
- `exam_id` — `null` для не-экзаменационных требований.
- Все `is_demo: true`, если не проверено по официальному источнику.

---

## 7. `data/knowledge_base/calendars.json` — календари экзаменов

**Владелец файла — B3.** Формат описан здесь для справки, потому что B1 использует его в `get_exam_format` через узлы `TestDate`.

### Схема

```json
[
  {
    "exam_id": "SAT_MATH",
    "date": "2026-11-07",
    "registration_deadline": "2026-10-10",
    "late_deadline": "2026-10-22",
    "source": "https://satsuite.collegeboard.org/sat/registration/dates-deadlines",
    "checked_at": "2026-09-17",
    "is_demo": false
  }
]
```

### Правила

- Узлы `Exam` создаёт B1 в `seed_skills`. B3 только дописывает `TestDate` после.
- `late_deadline` — `null`, если поздней регистрации нет.

---

## Как валидировать

```bash
cd backend
uv run python scripts/seed.py --validate --data-dir ../data
```

Проверяет синтаксис всех JSON, уникальность `id` в каталоге заблуждений, ссылки `skill_ids` на существующие навыки, суммы весов, DAG `REQUIRES`, шаблоны через `validate_template`.

## Что дальше

- **B1** — `data/misconceptions/*.json`, `data/skills/*.json`, `data/exam_formats/*.json`, `data/templates/sat/{alg,adv}/**`, `data/knowledge_base/{exams,routes}.json`.
- **B3** — `data/knowledge_base/calendars.json`, `data/programs_floor/programs.json`, `data/users.json`, `data/templates/sat/{psda,geo}/**`, `data/misconceptions/{psda,geo}.json`.
- **B2** — `data/templates/ent/**`, `data/misconceptions/ent_*.json`.

Любое изменение формата — сначала в этот файл, потом в код.