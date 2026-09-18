# Чек-лист ручной проверки — ЕНТ, область alg (первый живой прогон)

Проверка по product-logic.md §5.4: ровно один верный (`mcq`)/заявленное множество (`multi_select`)/одна величина (`numeric`); решение сходится с ключом; каждый дистрактор не является верным и выводится из конкретной ошибки; нет «все верны» и двусмысленностей; сложность соответствует эталону; формулировка на языке экзамена; нет дубликатов. Каждый пройденный `correct` пересчитан руками на 2–3 наборах параметров.

## Прошли проверку

| template_id | навык | проверен | замечание |
| :---- | :---- | :---- | :---- |
| `tpl.ent.alg.linear_eq_mcq5` | math.alg.linear_eq | да (существовал до прогона, не трогал) | — |
| `tpl.ent.alg.quadratic_conditions_multi` | math.alg.quadratic_roots | да (существовал до прогона, не трогал) | — |
| `tpl.ent.alg.linear_eq_multi_select` | math.alg.linear_eq | да | математика верна (проверено на 3 подстановках); все 3 дистрактора без `misconception_id` — в библиотеке нет заблуждения под ошибку «переносит слагаемое через „=“, не меняя знак» для обычного уравнения (см. sync-log 2026-09-18 21:35, B2 -> B1) |
| `tpl.ent.alg.linear_ineq_multi_select` | math.alg.linear_ineq | да | — |
| `tpl.ent.alg.linear_ineq_numeric` | math.alg.linear_ineq | да | — |
| `tpl.ent.alg.abs_value_eq_multi_select` | math.alg.abs_value_eq | да | оба корня — верное множество для `multi_select`, никакой двусмысленности |
| `tpl.ent.alg.abs_value_eq_numeric` | math.alg.abs_value_eq | да | спрашивает сумму корней — численно однозначно там, где `mcq5`-вариант того же уравнения был неоднозначен (см. отброшенные) |
| `tpl.ent.alg.quadratic_factor_numeric` | math.alg.quadratic_roots | да | Виета проверена на 3 парах корней |
| `tpl.ent.alg.quadratic_vieta_multi` | math.alg.quadratic_roots | да | — |
| `tpl.ent.alg.ineq_abs_value` | ent.alg.inequalities | да | двойное неравенство проверено на 2 наборах параметров, включая случай отрицательной нижней границы |
| `tpl.ent.alg.ineq_quadratic_int_count` | ent.alg.inequalities | да | подсчёт целых решений проверен на 2 наборах, формула `q - p - 1` верна независимо от разрыва между корнями |

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
