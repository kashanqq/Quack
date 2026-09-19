# Чек-лист ручной проверки — ЕНТ, область alg (первый живой прогон)

Проверка по product-logic.md §5.4: ровно один верный (`mcq`)/заявленное множество (`multi_select`)/одна величина (`numeric`); решение сходится с ключом; каждый дистрактор не является верным и выводится из конкретной ошибки; нет «все верны» и двусмысленностей; сложность соответствует эталону; формулировка на языке экзамена; нет дубликатов. Каждый пройденный `correct` пересчитан руками на 2–3 наборах параметров.

## Прошли проверку

| template_id | навык | проверен | замечание |
| :---- | :---- | :---- | :---- |
| `tpl.ent.alg.linear_eq_mcq5` | math.alg.linear_eq | да (существовал до прогона, не трогал) | — |
| `tpl.ent.alg.quadratic_conditions_multi` | math.alg.quadratic_roots | да (существовал до прогона, не трогал) | — |
| `tpl.ent.alg.linear_eq_multi_select` | math.alg.linear_eq | да, переписан (см. «Повторная проверка» ниже) | математика верна (проверено на 3 подстановках); дистракторы без `misconception_id` — в библиотеке нет заблуждения под ошибку «переносит слагаемое через „=“, не меняя знак» для обычного уравнения (см. sync-log 2026-09-18 21:35, B2 -> B1) |
| `tpl.ent.alg.linear_ineq_multi_select` | math.alg.linear_ineq | да, переписан (см. «Повторная проверка» ниже) | — |
| `tpl.ent.alg.linear_ineq_numeric` | math.alg.linear_ineq | да, поправлен (см. «Повторная проверка» ниже) | — |
| `tpl.ent.alg.abs_value_eq_multi_select` | math.alg.abs_value_eq | да | оба корня — верное множество для `multi_select`, никакой двусмысленности |
| `tpl.ent.alg.abs_value_eq_numeric` | math.alg.abs_value_eq | да | спрашивает сумму корней — численно однозначно там, где `mcq5`-вариант того же уравнения был неоднозначен (см. отброшенные) |
| `tpl.ent.alg.quadratic_factor_numeric` | math.alg.quadratic_roots | да, поправлен (см. «Повторная проверка» ниже) | Виета проверена на 3 парах корней |
| `tpl.ent.alg.quadratic_vieta_multi` | math.alg.quadratic_roots | да, переписан (см. «Повторная проверка» ниже) | — |
| `tpl.ent.alg.ineq_abs_value` | ent.alg.inequalities | да | двойное неравенство проверено на 2 наборах параметров, включая случай отрицательной нижней границы |
| `tpl.ent.alg.ineq_quadratic_int_count` | ent.alg.inequalities | да, поправлен (см. «Повторная проверка» ниже) | подсчёт целых решений проверен на 2 наборах, формула `q - p - 1` верна независимо от разрыва между корнями |

## Итог по навыкам области alg

| skill_id | шаблонов прошло проверку |
| :---- | :---- |
| math.alg.linear_eq | 2 |
| math.alg.linear_ineq | 2 |
| math.alg.quadratic_roots | 3 |
| math.alg.abs_value_eq | 2 |
| ent.alg.inequalities | 2 |

Все 5 навыков ≥ 2 — условие §4 ТЗ выполнено.

## Отброшены (удалены с диска)

| template_id | навык | причина |
| :---- | :---- | :---- |
| `tpl.ent.alg.quadratic_discriminant_mcq5` | math.alg.quadratic_roots | автоматика: `distractors collapse` + `seed failure rate: 50/50` (константы дискриминанта требовали точный квадрат и делимость одновременно — не выполнялось почти ни на одной подстановке) |
| `tpl.ent.alg.inequalities_quadratic_interval_mcq5` | ent.alg.inequalities | автоматика: `seed failure rate: 50/50` |
| `tpl.ent.alg.inequalities_rational_system_multi` | ent.alg.inequalities | автоматика: `seed failure rate: 12/50` |
| `tpl.ent.alg.inequalities_rational_interval_mcq5` | ent.alg.inequalities | автоматика: `seed failure rate: 50/50` |
| `tpl.ent.alg.inequalities_system_linear_multi_select` | ent.alg.inequalities | автоматика: `seed failure rate: 50/50` |
| `tpl.ent.alg.abs_value_eq_mcq5` | math.alg.abs_value_eq | ручная проверка: уравнение `\|ax−b\|=c` имеет два верных корня, но `mcq5` требует один ответ — второй настоящий корень был помещён в `distractors` с `misconception_id`, что фактически неверно (правильный ответ отмечен как ошибка) |
| `tpl.ent.alg.linear_eq_multi_select` (первая версия, до перегенерации) | math.alg.linear_eq | ручная проверка: 2 из 3 дистракторов помечены `lib.inequality_sign_flip`/`lib.inequality_endpoint` — заблуждения из библиотеки неравенств, не имеющие отношения к обычному уравнению без интервалов |
| `tpl.ent.alg.inequalities_quadratic_discriminant_numeric` | ent.alg.inequalities | ручная проверка: стем — `ax²+bx−c≥0`, а `correct`/`constraints` считали дискриминант как для `ax²+bx+c` (`b²−4ac` вместо `b²+4ac`); проверено численно (a=1,b=3,c=2): заявленный корень x=−2 не удовлетворяет исходному неравенству (−4 < 0) |
| `tpl.ent.alg.inequalities_quadratic_factorable_numeric` | ent.alg.inequalities | ручная проверка: `correct = r-1` не является решением, когда `r = q+1` (соседние целые корни) — проверено на p=1,q=2,r=3: `f(2) = 0`, не `< 0` |
| `tpl.ent.alg.inequalities_quadratic_interval_multi_select` | ent.alg.inequalities | ручная проверка: стем обещает список чисел («какие из следующих чисел»), но ни одного числа не перечисляет; плюс та же ошибка соседних целых корней, что выше |
| `tpl.ent.alg.inequalities_rational_interval_numeric` | ent.alg.inequalities | ручная проверка: решение само вывело интервал `[q; r)` как часть ответа, но `correct = q` — наименьшее, а не наибольшее число этого промежутка; наибольшее — `r-1` (проверено численно: p=1,q=5,r=9 → верно 8, не 5) |
| `tpl.ent.alg.inequalities_system_linear_mcq5` | ent.alg.inequalities | ручная проверка: дистрактор помечен `lib.quadratic_no_check` (заблуждение о дискриминанте квадратного уравнения) для линейной системы без единого квадратного члена — несвязанная метка |
| `tpl.ent.alg.ineq_system_multi` | ent.alg.inequalities | ручная проверка: собственный текст решения модели признаёт «система не имеет решений, проверьте условие» и молча подменяет второе неравенство на другое — стем математически не соответствует ответу |
| `tpl.ent.alg.linear_eq_fraction_mcq5` | math.alg.linear_eq | ручная проверка: формула `correct` не совпадает с уравнением стема; проверено численно (a=2,b=1,c=3,d=4): прямое решение даёт x=−0.25, шаблон утверждает −0.4 |

## Правки промпта (`app/agents/prompts/gen_template_v1.md`, калибровка одного и того же промпта, без v2)

1. Уточнение по дистракторам: тег `misconception_id` должен подходить по смыслу задаче (запрет переносить `inequality_*`/`quadratic_no_check` на задачи без неравенств/дискриминанта); при отсутствии подходящего заблуждения — `null`, а не чужой по смыслу id.
2. Уточнение по `solution`: все шаги считаются по одной и той же формуле без противоречий; для `a·x²+b·x−c` дискриминант — именно `b²+4ac`, а не формула от `a·x²+b·x+c`.
3. Новый пункт «Ответ на границе интервала»: для «наибольшего/наименьшего целого» рядом с корнем/границей требовать разрыв `>= 2` между соседними корнями в `constraints`, либо (для нестрогих неравенств) возвращать саму включённую границу — и каждый раз руками проверять, какой именно край (наибольший или наименьший) спрашивает `stem`.
4. Новый пункт «`multi_select` "выберите из следующих чисел"»: если стем обещает список чисел — перечислять их прямо в стеме, иначе не давать такую формулировку.
5. Новый пункт «Ответ — число, не промежуток»: `correct`/`distractors[].expr`/`trap_answers[].expr` — не текстовая интервальная запись (`(-∞, p) ∪ (q, r)`), а то, что понимает `sympy.parse_expr`; для неравенств формулировать вопрос так, чтобы ответом было число.

После пункта 5 три из четырёх новых генераций для `ent.alg.inequalities` прошли автоматику и ручную проверку с первого раза (`ineq_abs_value`, `ineq_quadratic_int_count`, `ineq_system_multi`); `ineq_system_multi` всё равно отброшен вручную — калибровка промпта закрыла классы ошибок 1, 3 (частично) и 5, но не гарантирует смысловую согласованность самой системы неравенств, это не покрыть общим правилом без потери общности промпта.

## Повторная проверка — плейсхолдеры доходят до ученика (2026-09-18, отдельный проход)

Внешняя проверка нашла: варианты `multi_select` не рендерятся вообще (`_build_multi_select` в `app/tasks/generate.py` берёт `str(d.expr)`/`str(x)` без подстановки — это код B1, не мой), а в `solution` составные выражения внутри `{...}` (`{c - b}`, `{p*p - 4*q}`, `{answer - 1}`) не подставляются, потому что `render_stem` рендерит только одно имя параметра или `{answer}` в фигурных скобках — обе особенности зафиксированы в `docs/data-formats.md`, значит содержимое шаблонов было вне контракта. Затронуты 6 файлов, все мои (`data/templates/ent/alg/`); собственный шаблон B1 `quadratic_conditions_multi.json` страдает тем же дефектом (`сумма корней равна {p}`) — не мой файл, не трогаю, см. sync-log.

Что исправлено:

| template_id | что было | что стало |
| :---- | :---- | :---- |
| `tpl.ent.alg.quadratic_vieta_multi` | `correct`/`distractors`/`omission_traps` содержали `{p}`/`{q}` — в `multi_select` не рендерятся, ученик видел бы `x₁ + x₂ = −{p}`; `solution` содержал составное `{p*p - 4*q}` | варианты переписаны как качественные утверждения без чисел и параметров («сумма корней равна коэффициенту при x, взятому с противоположным знаком» и т.п.) — верность не зависит от конкретных p, q; `solution` больше не показывает численное значение дискриминанта, только «по условию D > 0» |
| `tpl.ent.alg.linear_eq_multi_select` | `correct`/`distractors` содержали составные `{(c - b)/a}` и т.п. — не рендерятся нигде, тем более в `multi_select` | варианты переписаны как качественные утверждения о свойствах уравнения («уравнение имеет единственный корень», «чтобы найти корень, обе части нужно разделить на коэффициент при x») |
| `tpl.ent.alg.linear_ineq_multi_select` | `correct`/`distractors` — литеральный текст `x ≤ (c - b)/a` с буквами параметров без подстановки (даже не в `{}`, просто буквы a, b, c на виду у ученика); `solution` содержал составное `{c - b}` (дублирующая строка) | варианты переписаны как качественные утверждения про направление луча и включение границы (не зависят от чисел, так как a > 0 всегда по `constraints`); дублирующая строка `solution` с составным выражением убрана |
| `tpl.ent.alg.linear_ineq_numeric` | `solution` содержал составные `{c - b}` (дублирующая строка) и `{answer - 1}` (не рендерится; к тому же `{answer}` в этом шаблоне уже равен финальному сдвинутому ответу — строка задваивала −1) | дублирующая строка убрана; последний шаг переписан так, чтобы `{answer}` подставлялся один раз и только там, где он действительно равен ответу |
| `tpl.ent.alg.ineq_quadratic_int_count` | `solution` содержал составные `{p+1}`, `{p+2}`, `{q-1}` | заменено словесным описанием: «все целые числа, большие {p} и меньшие {q}» (оба — бэйр-подстановки) |
| `tpl.ent.alg.quadratic_factor_numeric` | `solution` дважды содержал составное `{r1 + r2}` | заменено на две отдельные подстановки с текстовым `+` между ними: `{r1} + {r2}` — рендерится корректно, включая скобки вокруг отрицательного `r2` (правило `render_stem` про минус после оператора) |

Проверка: `generate_instance` на 3 сидах для всех 11 файлов области — ни одного `{` в `stem_rendered`/текстах вариантов/`solution_rendered`/`trap_answers`, кроме `quadratic_conditions_multi.json` (не мой файл). `validate_template` — 0 ошибок на всех 11.

Правки промпта (пп. 6–7, тот же файл, без v2):

6. Новый пункт «Никаких `{...}` в текстах вариантов `multi_select`»: движок не рендерит эти тексты вообще, поэтому в них — только качественные утверждения без чисел и без имён параметров.
7. Новый пункт «Никаких составных выражений внутри `{...}`»: фигурные скобки подставляют ровно одно имя (параметр или `{answer}`); посчитанную величину — словами, отдельными подстановками с текстовым оператором между ними, или через отдельный параметр.

Плюс: `scripts/gen_templates.py` перед записью каждого прошедшего `validate_template` шаблона теперь рендерит его на 3 сидах и отбрасывает, если в `stem_rendered`, текстах вариантов или `solution_rendered` остался символ `{` — тест на эту проверку в `backend/tests/scripts/test_gen_templates.py::test_generation_drops_template_with_leftover_placeholder`.

## Повторная проверка — незаскобленные отрицательные значения (2026-09-18, ещё один проход)

Правило скобок в `render_stem` (`app/tasks/render.py`, файл B1) добавляет скобки вокруг подставленного отрицательного значения только если символ перед `{имя}` — один из ASCII `+-*/`. Наши шаблоны местами ставят перед плейсхолдером типографские «−» (U+2212) и «·» (U+00B7), которые в этот набор не входят: подстановка отрицательного значения тогда выглядит как `4·-2` вместо `4·(-2)`, а `−{p}` при p=−6 — как `−-6`. Проверено прогоном `generate_instance` на 40 сидах по всем 11 файлам области.

Затронуты 2 файла:

| template_id | что было | что стало |
| :---- | :---- | :---- |
| `tpl.ent.alg.quadratic_vieta_multi` | `"...равна −{p}, ..."` — типографский «−» перед плейсхолдером, при p<0 рендерится `−-6`; `"D = {p}² − 4·{q}."` — типографская «·» перед `{q}`, при q<0 рендерится `4·-2` | первая строка: типографский «−» заменён на ASCII `-{p}` — `render_stem` теперь сам добавляет скобки (`-(-6)`); вторая строка переформулирована словами без подстановки: «Дискриминант данного уравнения D = p² − 4q положителен по условию…» |
| `tpl.ent.alg.ineq_quadratic_int_count` | стем `(x − {p})(x − {q})` — типографский «−» перед `{p}` (p всегда отрицателен по `constraints`, диапазон [-6,-2]), рендерится `(x − -3)`; `solution` — `{q} − {p} − 1` тем же дефектом | типографские «−» перед плейсхолдерами заменены на ASCII `-`: `(x - {p})(x - {q})` и `{q} - {p} - 1` — скобки добавляются автоматически |

`tpl.ent.alg.quadratic_factor_numeric` проверен тем же прогоном на 40 сидах и дефекта не показал: единственные вхождения `−p`/`−{r1 + r2}`-подобного текста в файле — это либо буква `p` как литеральный текст общей формулы (не подстановка), либо `{r1}`/`{r2}` в позициях, где перед ними стоит `(`, `=` или слово, а не оператор — правкой не тронут.

Проверка (40 сидов на все 11 файлов через `generate_instance`, поиск паттерна «оператор (ASCII или типографский) + необязательный пробел + „-“ + цифра»): 0 совпадений на всех 10 моих файлах; `quadratic_conditions_multi.json` (B1) вне проверки, у него всё ещё открыт отдельный дефект с плейсхолдерами (см. sync-log). `validate_template` — 0 ошибок на всех 11.

Правка промпта (п. 8, тот же файл, без v2): пока не добавлял — источник этого класса ошибок в движке (`render_stem`), а не в тексте, который придумывает модель; сама модель не может знать, какие символы движок распознаёт как операторы. Сообщил B1 в sync-log с просьбой расширить набор операторов в `render_stem` на типографские «−», «·», «×», «÷» — после этого класс ошибок закроется на уровне движка для всех, а не только для новых генераций.

Плюс: `scripts/gen_templates.py` перед записью теперь дополнительно рендерит шаблон на 40 сидах и отбрасывает его, если в `stem_rendered`, текстах вариантов, `solution_rendered` или `trap_answers` встретится оператор (ASCII или типографский), сразу за которым — незаскобленное отрицательное число — тест `test_generation_drops_template_with_unparenthesized_negative` в `backend/tests/scripts/test_gen_templates.py`.

---

# Область num — «Числа и вычисления» (прогон 2026-09-18)

Прогон: `scripts/gen_templates.py --exam ENT_MATH --area num --n 3 --out data/templates/ent/num/` и четыре добора по навыкам, у которых после ручной проверки оставалось меньше двух шаблонов. Автоматика (инварианты `validate_template` на 50 сидах, проверка на остаток «{», проверка на незаскобленные отрицательные) здесь не дублируется — ниже только то, что проверено руками: `correct` пересчитан на двух подстановках, каждый дистрактор сверен со своим `misconception_id`, решение сверено с ответом.

## Прошли проверку

| template_id | навык | тип | проверен | замечание |
| :---- | :---- | :---- | :---- | :---- |
| `tpl.ent.num.percent.discount_numeric` | ent.num.percent | numeric | да (1150 и 30% → 805; 610 и 40% → 366) | ловушка «процент вместо новой цены» помечена `lib.percent_of_not_increase` из `psda.json` (файл B3) — ссылка зафиксирована в sync-log |
| `tpl.ent.num.percent.successive_increase_numeric` | ent.num.percent | numeric | да (10% и 25% → 37,5%; 30% и 50% → 95%) | ловушка `p1 + p2` — ровно то заблуждение, что описано в `lib.percent_of_not_increase` |
| `tpl.ent.num.powers.quotient_mcq5` | ent.num.powers | mcq5 | да (2⁶/2³ = 8; 3⁶/3² = 81) | поправлен: в решении стояло `{a}^(m−n)` — буквы доходили до ученика; заменено на `{a}^({m} − {n})`, последний шаг — «Ответ: вариант {answer}» |
| `tpl.ent.num.powers.nested_power_numeric` | ent.num.powers | numeric | да ((2⁴)³ = 4096; (4⁴)³ = 16777216) | поправлен так же: `{a}^(m·n)` → `{a}^({m}·{n})` |
| `tpl.ent.num.logarithm.def_mcq5` | ent.num.logarithm | mcq5 | да (log₃3² = 2; log₃3⁴ = 4) | поправлен: у дистрактора `a*k` снят `misconception_id` — ошибка «показатель умножил на основание» не описана ни одним заблуждением библиотеки |
| `tpl.ent.num.logarithm.odz_numeric` | ent.num.logarithm | numeric | да (x−4 = 2 → 6; x−5 = 4 → 9) | ловушки `c−b` и `b−c` дают значение, при котором аргумент логарифма отрицателен, — `lib.log_odz_skip` подходит по смыслу; у третьей (`a*c+b`) тег снят |
| `tpl.ent.num.progression.arith_geom_multi_select` | ent.num.progression | multi_select | да (a₁=3, d=2, b₁=4, q=2, n=4; a₁=2, d=2, n=4) | обозначения a₁, d, b₁, q введены в самом стеме, поэтому в вариантах они читаются |
| `tpl.ent.num.progression.arith_sum_multi_select` | ent.num.progression | multi_select | да (a₁=3, d=6, n=6; a₁=4, d=3, n=4) | поправлен: у `omission_trap` снят `lib.progression_term_off_by_one` — пропуск формулы Sₙ = n(a₁+aₙ)/2 не является ошибкой на единицу |

## Итог по навыкам области num

| skill_id | шаблонов прошло проверку |
| :---- | :---- |
| ent.num.percent | 2 |
| ent.num.powers | 2 |
| ent.num.logarithm | 2 |
| ent.num.progression | 2 |

Все 4 навыка ≥ 2 — условие §4 задания выполнено.

## Отброшены (удалены с диска)

Автоматикой — 44 из 54 сгенерированных. Преобладающие причины по убыванию частоты: составное выражение в `{...}` (`{m+n}`, `{q**n}`, `{100 - discount}`) — движок его не подставляет; `seed failure rate` — `constraints` требовали делимости и целого логарифма одновременно; `distractors collapse` — дистрактор совпадал с верным ответом или с другим дистрактором на части подстановок. Каждый класс закрыт правкой промпта (см. ниже).

Ручной проверкой:

| template_id | навык | причина |
| :---- | :---- | :---- |
| `tpl.ent.num.progression.arith_sum_multi` (первая версия) | ent.num.progression | верное утверждение «сумма первых n членов кратна n» ложно: a₁=1, d=3, n=6 даёт S=51, что на 6 не делится |
| `tpl.ent.num.logarithm.change_base_multi` | ent.num.logarithm | дистрактор «log_a(b) = log_a(c)·log_c(b)» — тождественно верное равенство, то есть второй правильный ответ в списке неверных |

# Область func — «Функции» (прогон 2026-09-18)

Прогон: `scripts/gen_templates.py --exam ENT_MATH --area func --n 3 --out data/templates/ent/func/` и шесть доборов по навыкам. Проверка — та же, что для num.

## Прошли проверку

| template_id | навык | тип | проверен | замечание |
| :---- | :---- | :---- | :---- | :---- |
| `tpl.ent.func.linear_inequality_integer_solution_numeric` | ent.func.linear | numeric | да (4x−7 < 3x+1 → 7; 3x−10 < 2x+1 → 10) | поправлены теги ловушек: «+1» → `lib.inequality_endpoint` (включил исключённую границу), у «−1» тег снят; стояли `lib.log_odz_skip` и `lib.vertex_sign_drop` — ни то, ни другое к линейному неравенству не относится |
| `tpl.ent.func.linear_inequality_count_integer_solutions_numeric` | ent.func.linear | numeric | да (2 < 2x < 10 → 3 числа; 4 < 3x < 10 → 2 числа) | то же исправление тегов; неравенство двустороннее, поэтому количество решений конечно |
| `tpl.ent.func.quadratic_axis_multi` | ent.func.quadratic | multi_select | да (a=1, b=2, c=10; a=1, b=6, c=1) | варианты качественные, без букв и чисел; `lib.vertex_sign_drop` стоит ровно на «абсцисса вершины положительна» |
| `tpl.ent.func.quadratic_vertex_ord_mcq5` | ent.func.quadratic | mcq5 | да (2x²+12x+8 → −10; x²+8x+4 → −12) | поправлен: последний шаг решения давал «y₀ = D» (для mcq `{answer}` — это буква варианта), переписан в «Ответ: вариант {answer}» |
| `tpl.ent.func.exponential_equation_same_base_numeric` | ent.func.exponential | numeric | да (5^(x+1) = 5⁴ → 3 на обеих подстановках) | убрана третья ловушка `n − m + c` (совпадала со второй на части подстановок) вместе с параметром `c`, который больше нигде не использовался |
| `tpl.ent.func.exponential_inequality_integer_solution` | ent.func.exponential | numeric | да (4^(x+1) < 4³ → 1) | ловушка `n − m` перепривязана к `lib.inequality_endpoint` (граница исключена строгим неравенством), у `m − n − 1` тег снят; неиспользуемый параметр `c` убран |
| `tpl.ent.func.logarithm_eq_odz_mcq5` | ent.func.logarithm | mcq5 | да (log₂(x+1) = log₂6 → 5; log₄(x+4) = log₄6 → 2) | поправлен: решение печатало «x = 6 − 1 = E» и «Проверяем ОДЗ: E > −1»; у дистрактора `c + b` снят тег `lib.log_odz_skip` (сложение вместо вычитания — не пропуск ОДЗ) |
| `tpl.ent.func.logarithm_properties_multi_select` | ent.func.logarithm | multi_select | да (утверждения общие, проверены при a=3 на парах M, N) | у двух дистракторов сняты теги: «логарифм суммы = сумма логарифмов» — не пропуск ОДЗ и не путаница оснований, подходящего заблуждения в библиотеке нет |
| `tpl.ent.func.derivative_tangent_slope_numeric` | ent.func.derivative | numeric | да (y = 3x², x₀ = 3 → 18; x₀ = 2 → 12) | добавлены `x0 ≥ 2` и `x0 != n − 1`: при `x0 = 1` ловушка `a·n·x0^n` совпадала с верным ответом, при `x0 = n − 1` — две ловушки между собой |
| `tpl.ent.func.derivative_power_rule_value_numeric` | ent.func.derivative | numeric | да (y = 5x⁵, x₀ = 2 → 400; y = 4x⁵, x₀ = 2 → 320) | те же два ограничения по той же причине; все три ловушки — три разных способа ошибиться в правиле (x^n)′ = n·x^(n−1) |

## Итог по навыкам области func

| skill_id | шаблонов прошло проверку |
| :---- | :---- |
| ent.func.linear | 2 |
| ent.func.quadratic | 2 |
| ent.func.exponential | 2 |
| ent.func.logarithm | 2 |
| ent.func.derivative | 2 |

Все 5 навыков ≥ 2 — условие §4 задания выполнено.

## Отброшены (удалены с диска)

Автоматикой — 49 из 69 сгенерированных; преобладающая причина в этой области — `seed failure rate` (ограничения на «красивый» ответ не выполнялись почти ни на одной подстановке), затем составные выражения в `{...}` и `distractors collapse`.

Ручной проверкой:

| template_id | навык | причина |
| :---- | :---- | :---- |
| `tpl.ent.func.linear_parallel_perpendicular_multi_select` | ent.func.linear | дистрактор содержит деление на ноль в самом тексте («точка с абсциссой x = (b2 − b1)/(k − k)»), два тега не связаны с задачей |
| `tpl.ent.func.linear_inequality_count_integer_solutions_numeric` (первая версия) | ent.func.linear | вопрос «сколько целых x удовлетворяют 3x − 4 < 2x + 5» ответа не имеет: неравенство одностороннее, таких чисел бесконечно много, а шаблон утверждал «8» |
| `tpl.ent.func.linear_slope_from_two_points_numeric` (две версии) | ent.func.linear | стем показывает невычисленную арифметику «A(1; 5*1 + 4)», ловушка `b` совпадает с верным ответом `k` на всех подстановках, где `b == k` |
| `tpl.ent.func.exponential_substitution_multi_select` | ent.func.exponential | варианты ссылаются на буквы `p`, `q`, которых в условии нет: ученик видит «2^(2x) − 5·2^x + 4 = 0» и вариант «сумма корней равна log_a(q)» |
| `tpl.ent.func.exponential_substitution_roots_multi_select` | ent.func.exponential | то же самое с `r1`, `r2` |
| `tpl.ent.func.exponential_equation_different_bases` | ent.func.exponential | ответ приводится к виду `log((9/2)**(1/log(2)))` — не число и не форма из `answer_forms`; в решении остаётся литеральная буква `n` |
| `tpl.ent.func.derivative_vertex_abscissa_mcq5` | ent.func.derivative | навык `ent.func.derivative`, но ни в условии, ни в решении производной нет — это задача на формулу вершины параболы |
| `tpl.ent.func.derivative_extremum_multi_select` | ent.func.derivative | верный вариант «абсцисса точки экстремума равна b/(2a)» ложен при стандартном чтении: в условии y = 3x² − 6x + 4, то есть b = −6, и правильна как раз формула −b/(2a), помеченная как дистрактор |
| `tpl.ent.func.derivative_increasing_interval_multi_select` | ent.func.derivative | варианты сформулированы через `p` и `q`, которых в условии нет: стем показывает «(x − 2)(x − 6)» |

# Правки промпта по итогам двух областей

Файл тот же (`app/agents/prompts/gen_template_v1.md`, без v2), правился только там, где один и тот же дефект встречался у трёх и более шаблонов. Добавлены раздел «Самопроверка перед ответом» (промежуточные числа в `solution`; ровно одно имя внутри `{...}`; никаких фигурных скобок в вариантах `multi_select`; различимость дистракторов на каждой подстановке, а не «вообще»; выполнимость `constraints` на большинстве сидов, через `choices` вместо фильтров; форма `correct` под тип задания) и пункты:

1. показатель степени не пишется в фигурных скобках (`a^{m+n}` — это плейсхолдер, а не верхний индекс);
2. в `correct` и дистракторах нет неизвестной `x` — ответом служит число;
3. перед подстановкой, которая может быть отрицательной, — ASCII-операторы, иначе движок не ставит скобки;
4. `{answer}` вне `numeric` — буква варианта, поэтому только отдельной строкой «Ответ: вариант {answer}»;
5. варианты `multi_select` не ссылаются на буквы, которых нет в условии;
6. `trap_answers` код не проверяет — различимость ловушек проверяю сам; параметр, нужный только ловушке, не завожу;
7. стем показывает числа, а не невычисленную арифметику, и спрашивает конечную величину.

Эффект по доле прошедших автоматику: первый прогон области num — 1 из 12, последние прогоны обеих областей — 3 из 9 и 2 из 3.

# Дефекты движка, найденные в этом проходе (не мои файлы — в sync-log)

- `validate_template` не проверяет `trap_answers` вообще: ловушка `numeric`-шаблона может совпасть с верным ответом или с другой ловушкой на части сидов, и шаблон всё равно пройдёт. Найдено на трёх своих шаблонах (исправлены ограничениями), воспроизводится и на шаблоне области alg `tpl.ent.alg.quadratic_factor_numeric` (мой файл, чиню отдельной веткой — эта ветка область alg не трогает).
- Ранее сообщённый дефект `quadratic_conditions_multi.json` (файл B1, плейсхолдер `{q}` в тексте варианта) по-прежнему открыт.

---

# Область trig — «Тригонометрия» (прогон 2026-09-19)

Прогон: `scripts/gen_templates.py --exam ENT_MATH --area trig --n 3 --out data/templates/ent/trig/` плюс пять доборов по навыкам, не набравшим двух проверенных шаблонов, и два диагностических вызова вне скрипта (скрипт печатает только счётчик `seed failure rate`, а причина отбраковки по нему не восстанавливается). Автоматика в чек-листе не дублируется; ниже — ручная проверка: две подстановки на шаблон, верность ответа, соответствие дистрактора своему `misconception_id`, согласованность решения с ответом.

В библиотеку `ent_trig.json` добавлены два заблуждения (`lib.cosine_law_sign`, `lib.trig_root_selection`) — до потолка в 4 записи на область.

## Прошли проверку

| template_id | навык | тип | проверен | замечание |
| :---- | :---- | :---- | :---- | :---- |
| `tpl.ent.trig.identities.reduction_sign_numeric` | ent.trig.identities | numeric | да (k=1, 30°; k=3, 60°) | поправлен: `k` ограничен нечётными, иначе ловушка «забыл знак» совпадала с ответом; 45° убран из `choices` (там sin = cos, две ловушки сливались); стем переписан в градусах вместо смеси π и градусов |
| `tpl.ent.trig.identities.pythagorean_cos_from_sin` | ent.trig.identities | numeric | да (sin = 4/5 → −3/5; sin = 4/7 → −√33/7) | `lib.trig_reduction_sign` на ловушке «положительный корень» подходит точно (знак по четверти); у двух других тегов сняты — подстановка синуса вместо косинуса заблуждением библиотеки не описана |
| `tpl.ent.trig.equations.sine_linear_interval` | ent.trig.equations | numeric | да (sin x = 2/3 → 2 корня; sin x = 1/2 → 2 корня) | теги «0» и «4» сняты, оставлен «1» с `lib.trig_period_missing` — ровно потеря второй серии |
| `tpl.ent.trig.equations.cos_linear_interval_count` | ent.trig.equations | numeric | да (cos x = 1/3 и 1/2 → по 2 корня) | — |
| `tpl.ent.trig.equations.tan_linear_interval` | ent.trig.equations | numeric | да (tan x = 2/3 и 1/2 → 1 корень на [0; π]) | — |
| `tpl.ent.trig.triangle.area_sides_angle` | ent.trig.triangle | numeric | да (10, 6, 90° → 30; 7, 8, 30° → 14) | ловушка «без множителя 1/2» перепривязана к `lib.area_half_dropped` из `ent_geo.json`; ловушка `a·b/2` убрана — при 30° и 90° она совпадала с ответом или с другой ловушкой |
| `tpl.ent.trig.triangle.cosine_law_side` | ent.trig.triangle | mcq5 | да (4, 5, 120° → √61; 6, 12, 60° → √108) | `lib.cosine_law_sign` стоит ровно на варианте с «+2ab·cos C»; у варианта с синусом вместо косинуса тег снят |
| `tpl.ent.trig.triangle_area_multi` | ent.trig.triangle | multi_select | да (10, 6, 90°; 7, 8, 30°) | та же перепривязка к `lib.area_half_dropped`; у варианта с косинусом и у `omission_trap` теги сняты |

## Итог по навыкам области trig

| skill_id | шаблонов прошло проверку |
| :---- | :---- |
| ent.trig.identities | 2 |
| ent.trig.equations | 3 |
| ent.trig.triangle | 3 |

## Отброшены (удалены с диска)

Автоматикой — 25 из 45 сгенерированных. Главная причина, найденная диагностическим прогоном: имена параметров в фигурных скобках внутри выражений ответа (`sqrt({a}^2 + {b}^2 - 2*{a}*{b}*cos({angle}*pi/180))`) — `sympy` читает `{a}` как множество и падает на каждом сиде. После правки промпта (п. 15) доля прошедших автоматику выросла с 1 из 9 до 6 из 9.

Ручной проверкой — 12:

| template_id | навык | причина |
| :---- | :---- | :---- |
| `tpl.ent.trig.equations_sin_linear_mcq5` (две версии) | ent.trig.equations | `correct` = π/6 при уравнении sin x = 1/{k}: верно только при k = 2; во второй версии arcsin({a}/2) = π/6 верно только при a = 1, а при a = 3 аргумент больше единицы |
| `tpl.ent.trig.equations_tan_linear_numeric` | ent.trig.equations | `correct` = π/4 при tan x = {m}, хотя `constraints` запрещают m = 1 |
| `tpl.ent.trig.equations_cos_quadratic_multi` | ent.trig.equations | решение объявляет корнями t² − pt + q именно p и q — при p = 3, q = 1 корни (3 ± √5)/2 |
| `tpl.ent.trig.equations.cosine_quadratic_roots` | ent.trig.equations | та же неверная факторизация 2t² − (p+q)t + pq, плюс «0 < 3/2 < 1» в решении и расхождение решения (4π) с `correct` (2π) |
| `tpl.ent.trig.equations.sine_quadratic_roots` | ent.trig.equations | та же факторизация; решение приходит к 2π, `correct` = 3π |
| `tpl.ent.trig.equations.tangent_quadratic_numeric` | ent.trig.equations | `correct` = π для суммы arctan(p) + arctan(q): при p = 4, q = 2 сумма равна 2.433 |
| `tpl.ent.trig.identities_double_angle_multi` | ent.trig.identities | стем «sin x = 3/1» — синус больше единицы; варианты через буквы a, b, которых в условии нет |
| `tpl.ent.trig.identities_sum_to_product_numeric` | ent.trig.identities | ловушка `2*sin((m+n)*pi/4)*cos((m-n)*pi/4)` — это та же сумма синусов, то есть тождественно верный ответ в списке ловушек |
| `tpl.ent.trig.identities_sum_to_product` | ent.trig.identities | варианты сформулированы через p и q, которых в условии нет (стем показывает sin(3x) + sin(4x)) |
| `tpl.ent.trig.identities.pythagorean_multi_select` | ent.trig.identities | стем «Дано: sin(α) = 60°» — синус приравнен к градусной мере угла |
| `tpl.ent.trig.identities.pythagorean_identity_numeric` | ent.trig.identities | ответ равен 1 при любых параметрах, ловушка `k` совпадает с ответом при k = 1, диагностики нет |

# Область geo — «Планиметрия» (прогон 2026-09-19)

Прогон: `--area geo --n 3 --out data/templates/ent/geo/` и один добор по `ent.geo.triangle`. Библиотека `data/misconceptions/ent_geo.json` заведена с нуля: `lib.pythagoras_leg_hypotenuse`, `lib.inscribed_angle_double`, `lib.area_half_dropped`, `lib.polygon_angle_sum`.

## Прошли проверку

| template_id | навык | тип | проверен | замечание |
| :---- | :---- | :---- | :---- | :---- |
| `tpl.ent.geo.triangle_angle_sum_multi` | ent.geo.triangle | multi_select | да (64° и 40°; 43° и 60°) | тег снят с варианта «угол C = 180° − угол A» — это не ошибка в формуле суммы углов многоугольника |
| `tpl.ent.geo.triangle_median_ratio_mcq5` | ent.geo.triangle | mcq5 | да (медиана 30 → 20; медиана 21 → 14) | оба тега сняты: «делит медиану пополам» в библиотеке отсутствует, а потолок в 4 записи на область уже выбран (см. sync-log) |
| `tpl.ent.geo.circle_inscribed_angle_mcq5` | ent.geo.circle | mcq5 | да (дуга 98° → 49°; 148° → 74°) | `lib.inscribed_angle_double` стоит на обоих «удвоенных» вариантах; последний шаг решения печатал «98° / 2 = A°» — переписан |
| `tpl.ent.geo.circle_inscribed_polygon_multi_select` | ent.geo.circle | multi_select | да (n = 7; n = 11) | — |
| `tpl.ent.geo.circle_tangent_radius_mcq5` | ent.geo.circle | mcq5 | да (d = 19, r = 6 → √325; d = 17, r = 5 → √264) | `lib.pythagoras_leg_hypotenuse` на «+r²» подходит точно; тег `lib.area_half_dropped` на «половине касательной» снят |
| `tpl.ent.geo.quadrilateral_parallelogram_area_mcq5` | ent.geo.quadrilateral | mcq5 | да (12 и 8 → 96; 12 и 9 → 108) | периметр и полупериметр помечены `lib.area_perimeter_mix` из `geo.json` (файл B3) — ссылка в sync-log |
| `tpl.ent.geo.quadrilateral_rhombus_diagonal_pythagoras_mcq5` | ent.geo.quadrilateral | mcq5 | да (10 и 8 → √41; 14 и 8 → √65) | добавлено `d1 > d2`: без него дистрактор √(d1² − d2²) давал мнимое число и показывался ученику как «12·√2·I» |
| `tpl.ent.geo.quadrilateral_trapezoid_midline_multi` | ent.geo.quadrilateral | multi_select | да (8 и 5; 8 и 3) | — |
| `tpl.ent.geo.polygon_angle_sum_mcq5` | ent.geo.polygon | mcq5 | да (n = 9 → 1260°; n = 7 → 900°) | `lib.polygon_angle_sum` на «180·n» — ровно описанное заблуждение |
| `tpl.ent.geo.polygon_regular_angle_mcq5` | ent.geo.polygon | mcq5 | да (n = 9 → 140°; n = 10 → 144°) | `lib.polygon_angle_sum` на «180/n» — вторая половина того же описания; тег с «180·(n − 2)» снят |

## Итог по навыкам области geo

| skill_id | шаблонов прошло проверку |
| :---- | :---- |
| ent.geo.triangle | 2 |
| ent.geo.circle | 3 |
| ent.geo.quadrilateral | 3 |
| ent.geo.polygon | 2 |

## Отброшены (удалены с диска)

Автоматикой — 4 из 15 (`seed failure rate`, `distractors collapse`, остаток `{` в тексте варианта `multi_select`).

Ручной проверкой — 1:

| template_id | навык | причина |
| :---- | :---- | :---- |
| `tpl.ent.geo.polygon_composite_area_multi` | ent.geo.polygon | при b = h четырёхугольник ABCD — прямоугольник, и вариант «четырёхугольник является прямоугольником» помечен дистрактором, то есть верное утверждение объявлено неверным; вдобавок решение содержит самовопрос «имеют одинаковую абсциссу? Нет, …» |

# Область stereo — «Стереометрия» (прогон 2026-09-19)

Прогон: `--area stereo --n 3 --out data/templates/ent/stereo/` и один добор по `ent.stereo.cylinder`. Библиотека `data/misconceptions/ent_stereo.json` заведена с нуля: `lib.volume_third_dropped`, `lib.lateral_vs_total_surface`, `lib.apothem_vs_height`, `lib.sphere_formula_swap`.

## Прошли проверку

| template_id | навык | тип | проверен | замечание |
| :---- | :---- | :---- | :---- | :---- |
| `tpl.ent.stereo.prism_rect_volume_mcq5` | ent.stereo.prism | mcq5 | да (4·12·11 = 528; 5·10·9 = 450) | ловушки перевода единиц помечены `lib.volume_units` из `geo.json` (файл B3); теги с двух «поверхностных» дистракторов сняты — путаницу объёма с поверхностью библиотека не описывает |
| `tpl.ent.stereo.prism_surface_multi` | ent.stereo.prism | multi_select | да (2×8×12; 6×10×12) | в стем внесены обозначения a, b, h — варианты ссылались на буквы, которых в условии не было; тег с «S_бок = a·b·h» снят |
| `tpl.ent.stereo.pyramid_regular_surface` | ent.stereo.pyramid | mcq5 | да (a = 10, апофема 6 → 220; апофема 9 → 280) | `lib.lateral_vs_total_surface` и `lib.apothem_vs_height` подходят точно; тег `lib.volume_third_dropped` на «2al/3» снят — в площади поверхности трети нет |
| `tpl.ent.stereo.pyramid_truncated_volume` | ent.stereo.pyramid | mcq5 | да (8, 2, 6 → 168; 10, 2, 9 → 372) | `lib.volume_third_dropped` на варианте без деления на 3 |
| `tpl.ent.stereo.cylinder_volume_numeric` | ent.stereo.cylinder | numeric | да (r = 5, h = 15 → 375π; r = 9, h = 14 → 1134π) | две ловушки «взял поверхность вместо объёма» убраны как непривязываемые, оставлены две ловушки перевода единиц с `lib.volume_units` |
| `tpl.ent.stereo.cylinder_inscribed_sphere_multi_select` | ent.stereo.cylinder | multi_select | да (r = 8; r = 7) | в стем внесено обозначение r; `omission_trap` ссылался на текст, которого нет среди верных вариантов, — заменён на «высота равна диаметру шара» с `lib.apothem_vs_height`; тег с «V цилиндра = πr³» снят |
| `tpl.ent.stereo.cone_surface_numeric` | ent.stereo.cone_sphere | numeric | да (r = 6, l = 8 → 48π) | `lib.lateral_vs_total_surface` на «πrl + πr²» подходит точно; тег с «πr²l» снят |
| `tpl.ent.stereo.sphere_surface_multi` | ent.stereo.cone_sphere | multi_select | да (R = 5; R = 8) | в стем внесено обозначение R; `lib.sphere_formula_swap` стоит на обеих перепутанных формулах |

## Итог по навыкам области stereo

| skill_id | шаблонов прошло проверку |
| :---- | :---- |
| ent.stereo.prism | 2 |
| ent.stereo.pyramid | 2 |
| ent.stereo.cylinder | 2 |
| ent.stereo.cone_sphere | 2 |

## Отброшены (удалены с диска)

Автоматикой — 7 из 15 (`seed failure rate` на «красивых» ответах с π, `distractors collapse` на совпадающих формулах поверхности). Ручной проверкой не отброшено ни одного: после правок промпта по итогам trig и geo содержательных ошибок в этой области не нашлось.

# Правки промпта по итогам трёх областей

Файл тот же (`app/agents/prompts/gen_template_v1.md`, без v2), правился по дефектам с тремя и более повторами. Добавлены пункты:

13. `correct` — функция параметров, а не одно табличное значение (arcsin({a}/2) = π/6 верно только при a = 1); диапазоны параметров обязаны давать осмысленные условия (sin x = a/b требует a < b);
14. π в ответе ученик видит числом (`pi/6` печатается как `0.524`), поэтому «ответ, выраженный через π» не спрашиваем;
15. в `correct`, `distractors[].expr`, `trap_answers[].expr` имена параметров пишутся без фигурных скобок — `sympy` читает `{a}` как множество (главная причина отбраковки в trig: 4 шаблона подряд);
16. итоговое утверждение проверяется на двух числах, а не «по формуле из памяти» (неверная факторизация 2t² − (p+q)t + pq и сумма арктангенсов — три шаблона).

Плюс уточнён пункт 9 (`{answer}` вне `numeric` — буква варианта): добавлен пример с градусами, потому что в geo пять шаблонов подряд печатали «180°·(9 − 2) = B°».

# Дефект движка

`tpl.ent.alg.quadratic_factor_numeric` (область alg, найден на прошлом заходе) исправлен отдельным коммитом: добавлено `r1 + r2 != 0`, иначе ловушка `r1 + r2` совпадала с верным ответом `-(r1 + r2)` на противоположных корнях. Причина общая — `validate_template` не проверяет `trap_answers`; запрос к B1 в sync-log остаётся открытым, как и дефект плейсхолдера в `quadratic_conditions_multi.json` (файл B1).
