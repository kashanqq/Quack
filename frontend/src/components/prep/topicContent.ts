// What a topic holds inside a set: a minimal explanation (not a course — just enough to know what the
// topic is about), the usual trap, and a couple of short checks. Demo content until the backend
// generates it per student (product-logic §4.4: material is generated on request, not stored as a course).

import { CHECKS, type Task } from "./prepData";
import { ENT_CHECKS, ENT_TOPICS } from "./entContent";

export type TopicContent = {
  /** Two or three sentences: what the topic is and what the exam asks */
  summary: string;
  /** What you must be able to do */
  points: string[];
  example: { q: string; a: string };
  /** The mistake most students make here; the student's own traps come from the knowledge model */
  trap: string;
};

export const TOPICS: Record<string, TopicContent> = {
  /* ---------- SAT Math ---------- */
  linear: {
    summary: "Уравнение, где x только в первой степени: ax + b = c. Решается переносом слагаемых и делением на коэффициент.",
    points: ["Переносить слагаемые со сменой знака", "Раскрывать скобки перед решением", "Составлять уравнение по тексту задачи"],
    example: { q: "3x − 7 = 11", a: "3x = 18, значит x = 6" },
    trap: "Забыть сменить знак при переносе через «=».",
  },
  systems: {
    summary: "Два уравнения с двумя неизвестными, которые должны выполняться одновременно. Решение — точка пересечения двух прямых.",
    points: ["Подстановка: выразить одну переменную и подставить", "Сложение: уравнять коэффициенты и сложить", "Понимать, когда решений нет или бесконечно много"],
    example: { q: "x + y = 7, x − y = 1", a: "Сложим: 2x = 8, x = 4, тогда y = 3" },
    trap: "Найти x и забыть найти y — в ответе SAT часто спрашивают именно второе.",
  },
  abs: {
    summary: "|a| — расстояние от числа до нуля, поэтому оно не бывает отрицательным. Уравнение |x − a| = b при b > 0 даёт две точки: справа и слева от a.",
    points: ["Раскрывать модуль на две ветви: x − a = b и x − a = −b", "Проверять, что b ≥ 0, иначе решений нет", "Читать |x − a| как расстояние между x и a"],
    example: { q: "|2x − 1| = 5", a: "2x − 1 = 5 → x = 3; 2x − 1 = −5 → x = −2. Ответ: 3 и −2" },
    trap: "Взять только положительную ветвь и потерять второй корень.",
  },
  inequalities: {
    summary: "Как уравнение, но ответ — промежуток. Главное правило: при умножении или делении на отрицательное число знак неравенства переворачивается.",
    points: ["Переворачивать знак при делении на отрицательное", "Записывать ответ промежутком и рисовать на прямой", "Решать неравенства с модулем через расстояние"],
    example: { q: "−2x + 4 > 10", a: "−2x > 6, делим на −2 и переворачиваем: x < −3" },
    trap: "Разделить на отрицательное и не перевернуть знак.",
  },
  quadratics: {
    summary: "Функция вида ax² + bx + c, её график — парабола. На SAT спрашивают корни, вершину и то, как коэффициенты меняют график.",
    points: ["Находить корни через дискриминант или разложение", "Находить вершину: x = −b / 2a", "Понимать знак a: ветви вверх или вниз"],
    example: { q: "x² − 5x + 6 = 0", a: "(x − 2)(x − 3) = 0, корни 2 и 3" },
    trap: "Потерять минус при раскрытии скобок перед ними.",
  },
  polynomials: {
    summary: "Многочлен — сумма степеней x с коэффициентами. Корень многочлена — число, при котором он равен нулю, и тогда (x − корень) — его множитель.",
    points: ["Раскладывать на множители", "Связывать корни и множители", "Находить остаток от деления подстановкой"],
    example: { q: "Остаток от деления x³ − 2x + 5 на (x − 1)", a: "Подставим x = 1: 1 − 2 + 5 = 4" },
    trap: "Путать корень 3 и множитель (x + 3).",
  },
  exponential: {
    summary: "Функция, где x стоит в показателе: a · bˣ. Описывает рост и спад на один и тот же процент за шаг.",
    points: ["Отличать линейный рост от экспоненциального", "Переводить «растёт на 5%» в множитель 1,05", "Читать a как начальное значение"],
    example: { q: "Население 2000, растёт на 10% в год. Сколько через 2 года?", a: "2000 · 1,1² = 2420" },
    trap: "Прибавлять 10% от начального значения каждый год, как в линейном росте.",
  },
  statistics: {
    summary: "Среднее, медиана, размах и стандартное отклонение описывают набор данных. SAT проверяет, как они меняются, если добавить или убрать число.",
    points: ["Считать среднее и медиану", "Понимать, что выброс сильно двигает среднее, но не медиану", "Сравнивать разброс по графикам"],
    example: { q: "Данные 2, 3, 3, 4, 18: что больше, среднее или медиана?", a: "Среднее 6, медиана 3 — среднее больше из-за выброса 18" },
    trap: "Считать медиану, не отсортировав числа.",
  },
  probability: {
    summary: "Вероятность — доля благоприятных исходов среди всех. На SAT часто по таблице: нужно выбрать правильную строку или столбец как «все».",
    points: ["Считать вероятность по таблице двух признаков", "Различать «из всех» и «из тех, кто…»", "Складывать вероятности несовместных событий"],
    example: { q: "Из 40 учеников 12 играют в шахматы, из них 5 девочек. Вероятность, что шахматист — девочка?", a: "5 / 12 — делим на шахматистов, а не на всех 40" },
    trap: "Делить на общий итог таблицы, когда вопрос про подгруппу.",
  },
  triangles: {
    summary: "Подобные треугольники — одинаковой формы, разного размера. Стороны относятся с коэффициентом k, площади — с коэффициентом k².",
    points: ["Узнавать подобие по двум равным углам", "Составлять пропорцию соответственных сторон", "Помнить: площадь меняется как квадрат коэффициента"],
    example: { q: "Треугольники подобны, k = 2, площадь меньшего 5", a: "Площадь большего 5 · 2² = 20" },
    trap: "Умножить площадь на k вместо k².",
  },
  circle: {
    summary: "Центральный угол равен дуге, вписанный — половине дуги. Угол, опирающийся на диаметр, прямой. Из этого строится вся тригонометрия на SAT.",
    points: ["Вписанный угол = половина центрального на ту же дугу", "Угол на диаметр — 90°", "Длина дуги и площадь сектора через долю от 360°"],
    example: { q: "Центральный угол 80°. Чему равен вписанный на ту же дугу?", a: "80° / 2 = 40°" },
    trap: "Взять центральный угол вместо вписанного.",
  },
  trig: {
    summary: "Синус, косинус и тангенс — отношения сторон прямоугольного треугольника. SOH-CAH-TOA: противолежащий, прилежащий, гипотенуза.",
    points: ["sin = противолежащий / гипотенуза, cos = прилежащий / гипотенуза", "sin x = cos(90° − x)", "Переводить градусы в радианы: π = 180°"],
    example: { q: "Катеты 3 и 4. Синус угла против катета 3?", a: "Гипотенуза 5, sin = 3/5" },
    trap: "Путать противолежащий и прилежащий катет.",
  },
  reduction: {
    summary: "Формулы приведения сводят sin и cos любого угла к острому. Смотрим, в какой четверти угол, и меняется ли функция на «ко-».",
    points: ["Определять знак по четверти", "Менять sin ↔ cos при 90° и 270°", "Не менять функцию при 180° и 360°"],
    example: { q: "sin(180° − 30°)", a: "Вторая четверть, синус там положительный, функция не меняется: sin 30° = 1/2" },
    trap: "Поменять функцию при 180°, где она остаётся той же.",
  },
  ...ENT_TOPICS,
};

/** Checks for topics that had none in the demo pool, so every node in a set can be tested. */
const MORE_CHECKS: Record<string, Task[]> = {
  linear: [
    { id: "ln1", text: "Реши: 5 − 2x = 11", options: [{ label: "x = 3" }, { label: "x = −3", correct: true }, { label: "x = 8", trap: "Не сменил знак при переносе" }, { label: "x = −8" }] },
  ],
  systems: [
    { id: "sy1", text: "x + y = 10, x − y = 4. Чему равен y?", options: [{ label: "7", trap: "Нашёл x и ответил им" }, { label: "3", correct: true }, { label: "6" }, { label: "14" }] },
  ],
  inequalities: [
    { id: "iq1", text: "Реши: −3x ≥ 12", options: [{ label: "x ≥ −4", trap: "Не перевернул знак при делении на отрицательное" }, { label: "x ≤ −4", correct: true }, { label: "x ≤ 4" }, { label: "x ≥ 4" }] },
  ],
  quadratics: [
    { id: "qd1", text: "Абсцисса вершины параболы y = x² − 6x + 1?", options: [{ label: "−3", trap: "Потерял минус в −b / 2a" }, { label: "3", correct: true }, { label: "6" }, { label: "1" }] },
  ],
  polynomials: [
    { id: "pl1", text: "Число 2 — корень многочлена p(x). Какой множитель у p(x) точно есть?", options: [{ label: "(x + 2)", trap: "Перепутал знак корня и множителя" }, { label: "(x − 2)", correct: true }, { label: "(2x)" }] },
  ],
  exponential: [
    { id: "ex1", text: "Цена 100, растёт на 20% в год. Какая через 2 года?", options: [{ label: "140", trap: "Посчитал как линейный рост" }, { label: "144", correct: true }, { label: "120" }, { label: "240" }] },
  ],
  statistics: [
    { id: "st1", text: "К данным 4, 5, 6 добавили 30. Что изменится сильнее?", options: [{ label: "Медиана", trap: "Считает, что выброс сильнее двигает медиану" }, { label: "Среднее", correct: true }, { label: "Одинаково" }] },
  ],
  probability: [
    { id: "pr1", text: "В классе 30 человек, 10 в кружке, из них 4 мальчика. Вероятность, что участник кружка — мальчик?", options: [{ label: "4/30", trap: "Разделил на всех, а не на участников кружка" }, { label: "4/10", correct: true }, { label: "10/30" }] },
  ],
  trig: [
    { id: "tr1", text: "sin x = cos 30°. Чему равен острый угол x?", options: [{ label: "30°", trap: "Не узнал связь sin x = cos(90° − x)" }, { label: "60°", correct: true }, { label: "90°" }] },
  ],
  reduction: [
    { id: "rd1", text: "cos(180° − 60°) = ?", options: [{ label: "1/2", trap: "Не учёл знак косинуса во второй четверти" }, { label: "−1/2", correct: true }, { label: "√3/2" }] },
  ],
};

/** Extra questions so a topic's mock test is a few questions long, not one */
const MOCK_CHECKS: Record<string, Task[]> = {
  linear: [
    { id: "ln2", text: "Реши: 3(x − 2) = 12", options: [{ label: "x = 6", correct: true }, { label: "x = 4", trap: "Не раскрыл скобки: разделил 12 на 3 и забыл про −2" }, { label: "x = 2" }, { label: "x = 14/3" }] },
    { id: "ln3", text: "Прямая проходит через (0; 2) и (2; 6). Её угловой коэффициент?", options: [{ label: "2", correct: true }, { label: "4", trap: "Взял разность y без деления на разность x" }, { label: "1/2", trap: "Поделил Δx на Δy" }, { label: "3" }] },
  ],
  systems: [
    { id: "sy2", text: "2x + y = 7, x = 2. Чему равен y?", options: [{ label: "3", correct: true }, { label: "5", trap: "Подставил x, но не умножил на 2" }, { label: "2" }, { label: "11" }] },
    { id: "sy3", text: "Сколько решений у системы y = 2x + 1 и y = 2x − 3?", options: [{ label: "Ни одного", correct: true }, { label: "Одно", trap: "Не заметил, что прямые параллельны" }, { label: "Бесконечно много" }] },
  ],
  abs: [
    { id: "ab2", text: "Реши: |x + 1| = 4", options: [{ label: "x = 3 или x = −5", correct: true }, { label: "x = 3", trap: "Потерял отрицательную ветвь" }, { label: "x = −3 или x = 5", trap: "Перепутал знаки при раскрытии" }, { label: "x = 5" }] },
    { id: "ab3", text: "Сколько решений у |2x − 1| = −3?", options: [{ label: "Ни одного", correct: true }, { label: "Два", trap: "Раскрыл модуль, не проверив, что правая часть отрицательна" }, { label: "Одно" }] },
  ],
  inequalities: [
    { id: "iq2", text: "Реши: 2x − 5 < 3", options: [{ label: "x < 4", correct: true }, { label: "x > 4", trap: "Перевернул знак без деления на отрицательное" }, { label: "x < −1" }, { label: "x < 1" }] },
    { id: "iq3", text: "Какие x подходят под |x| < 3?", options: [{ label: "−3 < x < 3", correct: true }, { label: "x < 3", trap: "Забыл нижнюю границу" }, { label: "x < −3 или x > 3", trap: "Перепутал «меньше» и «больше» для модуля" }] },
  ],
  quadratics: [
    { id: "qd2", text: "Корни уравнения x² − 5x + 6 = 0?", options: [{ label: "2 и 3", correct: true }, { label: "−2 и −3", trap: "Перепутал знаки по теореме Виета" }, { label: "1 и 6" }, { label: "−1 и 6" }] },
    { id: "qd3", text: "Сколько корней у x² + 4x + 5 = 0?", options: [{ label: "Ни одного", correct: true }, { label: "Два", trap: "Не посчитал дискриминант: 16 − 20 < 0" }, { label: "Один" }] },
  ],
  polynomials: [
    { id: "pl2", text: "Остаток от деления p(x) = x³ − 2x + 1 на (x − 1)?", options: [{ label: "0", correct: true }, { label: "2", trap: "Подставил x = −1 вместо x = 1" }, { label: "1" }, { label: "−1" }] },
    { id: "pl3", text: "Упрости: (x² − 9) / (x − 3)", options: [{ label: "x + 3", correct: true }, { label: "x − 3", trap: "Неверно разложил разность квадратов" }, { label: "x² − 3" }, { label: "x + 9" }] },
  ],
  exponential: [
    { id: "ex2", text: "Население 1000, каждый год уменьшается на 10%. Какое через 2 года?", options: [{ label: "810", correct: true }, { label: "800", trap: "Посчитал как линейное убывание" }, { label: "900" }, { label: "819" }] },
    { id: "ex3", text: "В формуле y = 50 · (1,08)ᵗ что означает 1,08?", options: [{ label: "Рост на 8% за период", correct: true }, { label: "Рост на 108%", trap: "Принял множитель за процент роста" }, { label: "Начальное значение" }] },
  ],
  statistics: [
    { id: "st2", text: "Медиана набора 3, 9, 1, 7, 5?", options: [{ label: "5", correct: true }, { label: "1", trap: "Взял середину, не отсортировав" }, { label: "7" }, { label: "25" }] },
    { id: "st3", text: "У двух наборов одинаковое среднее, у первого разброс больше. Что это значит?", options: [{ label: "Значения первого дальше от среднего", correct: true }, { label: "У первого больше среднее", trap: "Перепутал разброс и среднее" }, { label: "Медианы равны" }] },
  ],
  probability: [
    { id: "pr2", text: "Бросают монету дважды. Вероятность двух орлов?", options: [{ label: "1/4", correct: true }, { label: "1/2", trap: "Не перемножил вероятности двух бросков" }, { label: "1/3" }, { label: "2/4" }] },
    { id: "pr3", text: "В мешке 3 красных и 5 синих. Вероятность достать синий?", options: [{ label: "5/8", correct: true }, { label: "5/3", trap: "Поделил на число красных, а не на все шары" }, { label: "3/8" }, { label: "1/2" }] },
  ],
  triangles: [
    { id: "tg2", text: "Треугольники подобны с коэффициентом 2. Во сколько раз отличаются площади?", options: [{ label: "В 4 раза", correct: true }, { label: "В 2 раза", trap: "Перенёс коэффициент сторон на площадь" }, { label: "В 8 раз" }] },
    { id: "tg3", text: "Катеты 6 и 8. Гипотенуза?", options: [{ label: "10", correct: true }, { label: "14", trap: "Сложил катеты вместо теоремы Пифагора" }, { label: "√28" }, { label: "48" }] },
  ],
  circle: [
    { id: "c3", text: "Уравнение (x − 2)² + (y + 1)² = 9. Центр и радиус?", options: [{ label: "(2; −1), r = 3", correct: true }, { label: "(−2; 1), r = 3", trap: "Взял знаки из скобок как есть" }, { label: "(2; −1), r = 9", trap: "Забыл извлечь корень из 9" }] },
  ],
  trig: [
    { id: "tr2", text: "В прямоугольном треугольнике катет против угла 3, гипотенуза 5. sin угла?", options: [{ label: "3/5", correct: true }, { label: "4/5", trap: "Перепутал синус и косинус" }, { label: "3/4" }, { label: "5/3" }] },
    { id: "tr3", text: "Сколько радиан в 180°?", options: [{ label: "π", correct: true }, { label: "2π", trap: "Перепутал с полным оборотом" }, { label: "π/2" }] },
  ],
  reduction: [
    { id: "rd2", text: "sin(90° + 30°) = ?", options: [{ label: "cos 30°", correct: true }, { label: "sin 30°", trap: "Не сменил функцию при 90°" }, { label: "−cos 30°", trap: "Поставил знак, как для косинуса во II четверти" }] },
    { id: "rd3", text: "tan(180° + 45°) = ?", options: [{ label: "1", correct: true }, { label: "−1", trap: "Не учёл, что тангенс в III четверти положителен" }, { label: "0" }] },
  ],
};

/** More demo questions, so every topic's mock is 6–8 long, the way the backend will build it */
const MOCK_MORE: Record<string, Task[]> = {
  linear: [
    { id: "m-ln4", text: "Реши: x/4 + 1 = 3", options: [{ label: "x = 8", correct: true }, { label: "x = 16", trap: "Умножил на 4 до того, как перенёс 1" }, { label: "x = 2" }, { label: "x = 4" }] },
    { id: "m-ln5", text: "Такси: 500 тг за посадку и 150 тг за км. Сколько стоит поездка на 6 км?", options: [{ label: "1400", correct: true }, { label: "3900", trap: "Умножил посадку на километры" }, { label: "900" }, { label: "650" }] },
    { id: "m-ln6", text: "При каком k прямые y = kx + 1 и y = 3x − 2 параллельны?", options: [{ label: "k = 3", correct: true }, { label: "k = −1/3", trap: "Взял условие перпендикулярности" }, { label: "k = −2" }, { label: "k = 1" }] },
  ],
  systems: [
    { id: "m-sy4", text: "3x + 2y = 12, x − 2y = 4. Чему равен x?", options: [{ label: "4", correct: true }, { label: "2", trap: "Вычел уравнения вместо сложения" }, { label: "8" }, { label: "0" }] },
    { id: "m-sy5", text: "Билеты: взрослый 3, детский 2, всего 10 билетов за 26. Сколько взрослых?", options: [{ label: "6", correct: true }, { label: "4", trap: "Нашёл детские и ответил ими" }, { label: "5" }, { label: "8" }] },
    { id: "m-sy6", text: "При каком a у системы x + y = 2 и 2x + 2y = a бесконечно много решений?", options: [{ label: "a = 4", correct: true }, { label: "a = 2", trap: "Не умножил правую часть вместе с левой" }, { label: "Ни при каком" }] },
  ],
  abs: [
    { id: "m-ab4", text: "Реши: |x − 3| < 2", options: [{ label: "1 < x < 5", correct: true }, { label: "x < 5", trap: "Потерял нижнюю границу" }, { label: "x < 1 или x > 5", trap: "Перепутал «меньше» с «больше» у модуля" }, { label: "−1 < x < 5" }] },
    { id: "m-ab5", text: "Чему равно |−7| − |3 − 5|?", options: [{ label: "5", correct: true }, { label: "9", trap: "Раскрыл |3 − 5| как −2 и вычел минус" }, { label: "−9" }, { label: "2" }] },
    { id: "m-ab6", text: "Реши: |x| = x − 4", options: [{ label: "Решений нет", correct: true }, { label: "x = 2", trap: "Не проверил корень подстановкой" }, { label: "x = 4" }] },
  ],
  inequalities: [
    { id: "m-iq4", text: "Реши: 5 − x > 2", options: [{ label: "x < 3", correct: true }, { label: "x > 3", trap: "Не перевернул знак при делении на −1" }, { label: "x < −3" }, { label: "x > −3" }] },
    { id: "m-iq5", text: "Сколько целых x удовлетворяют −2 ≤ x < 3?", options: [{ label: "5", correct: true }, { label: "4", trap: "Не включил границу со знаком ≤" }, { label: "6", trap: "Включил строгую границу" }] },
    { id: "m-iq6", text: "Реши: (x − 1)(x + 2) < 0", options: [{ label: "−2 < x < 1", correct: true }, { label: "x < −2 или x > 1", trap: "Перепутал знак на интервалах" }, { label: "x < 1" }] },
  ],
  quadratics: [
    { id: "m-qd4", text: "Сумма корней x² − 7x + 10 = 0?", options: [{ label: "7", correct: true }, { label: "−7", trap: "Забыл, что сумма корней — это −b/a" }, { label: "10" }, { label: "3" }] },
    { id: "m-qd5", text: "Наименьшее значение y = (x − 2)² + 5?", options: [{ label: "5", correct: true }, { label: "2", trap: "Взял абсциссу вершины вместо значения" }, { label: "−2" }, { label: "0" }] },
    { id: "m-qd6", text: "Реши: x² = 9x", options: [{ label: "x = 0 или x = 9", correct: true }, { label: "x = 9", trap: "Поделил на x и потерял корень 0" }, { label: "x = ±3" }] },
  ],
  polynomials: [
    { id: "m-pl4", text: "Раскрой: (x + 3)²", options: [{ label: "x² + 6x + 9", correct: true }, { label: "x² + 9", trap: "Потерял удвоенное произведение" }, { label: "x² + 3x + 9" }] },
    { id: "m-pl5", text: "Корни x³ − 4x = 0?", options: [{ label: "0, 2, −2", correct: true }, { label: "2, −2", trap: "Сократил на x и потерял корень 0" }, { label: "0, 4" }] },
    { id: "m-pl6", text: "Степень многочлена (x² + 1)(x³ − x)?", options: [{ label: "5", correct: true }, { label: "6", trap: "Перемножил степени вместо сложения" }, { label: "3" }] },
  ],
  exponential: [
    { id: "m-ex4", text: "2ˣ = 32. x = ?", options: [{ label: "5", correct: true }, { label: "16", trap: "Поделил 32 на 2" }, { label: "4" }, { label: "6" }] },
    { id: "m-ex5", text: "Бактерии удваиваются каждые 3 часа, было 100. Сколько через 9 часов?", options: [{ label: "800", correct: true }, { label: "600", trap: "Посчитал как линейный рост" }, { label: "300" }, { label: "900" }] },
    { id: "m-ex6", text: "Какая функция описывает убывание на 25% за период?", options: [{ label: "y = a · 0,75ᵗ", correct: true }, { label: "y = a · 0,25ᵗ", trap: "Взял процент убывания вместо остатка" }, { label: "y = a − 0,25t" }] },
  ],
  statistics: [
    { id: "m-st4", text: "Среднее 4 чисел равно 10. Сумма чисел?", options: [{ label: "40", correct: true }, { label: "10", trap: "Перепутал среднее и сумму" }, { label: "2,5" }, { label: "14" }] },
    { id: "m-st5", text: "Мода набора 2, 3, 3, 5, 7, 7, 7?", options: [{ label: "7", correct: true }, { label: "5", trap: "Взял медиану вместо моды" }, { label: "3" }] },
    { id: "m-st6", text: "Опрос в спортзале: «Сколько раз в неделю вы тренируетесь?» Можно ли переносить итог на всех жителей города?", options: [{ label: "Нет, выборка смещена", correct: true }, { label: "Да, если опрошенных много", trap: "Размер выборки не лечит её смещение" }] },
  ],
  probability: [
    { id: "m-pr4", text: "Кубик бросают один раз. Вероятность чётного числа?", options: [{ label: "1/2", correct: true }, { label: "1/3", trap: "Посчитал только 2 и 4" }, { label: "1/6" }] },
    { id: "m-pr5", text: "P(A) = 0,3. Чему равна P(не A)?", options: [{ label: "0,7", correct: true }, { label: "0,3", trap: "Не взял дополнение" }, { label: "−0,3" }] },
    { id: "m-pr6", text: "Из 5 учеников выбирают старосту и заместителя. Сколько вариантов?", options: [{ label: "20", correct: true }, { label: "10", trap: "Не учёл, что роли разные" }, { label: "25" }] },
  ],
  triangles: [
    { id: "m-tg4", text: "Сумма углов треугольника 180°, два угла 50° и 60°. Третий?", options: [{ label: "70°", correct: true }, { label: "110°", trap: "Сложил два угла и остановился" }, { label: "90°" }] },
    { id: "m-tg5", text: "Тень столба 6 м, тень человека ростом 1,8 м — 2 м. Высота столба?", options: [{ label: "5,4 м", correct: true }, { label: "6,6 м", trap: "Прибавил вместо пропорции" }, { label: "3,6 м" }] },
    { id: "m-tg6", text: "В равнобедренном треугольнике угол при вершине 40°. Угол при основании?", options: [{ label: "70°", correct: true }, { label: "40°", trap: "Решил, что все углы равны вершинному" }, { label: "140°" }] },
  ],
  circle: [
    { id: "m-c4", text: "Длина окружности радиуса 5?", options: [{ label: "10π", correct: true }, { label: "25π", trap: "Посчитал площадь вместо длины" }, { label: "5π" }] },
    { id: "m-c5", text: "Дуга 90° в круге радиуса 4. Её длина?", options: [{ label: "2π", correct: true }, { label: "4π", trap: "Взял половину окружности вместо четверти" }, { label: "π" }] },
    { id: "m-c6", text: "Вписанный угол опирается на диаметр. Он равен…", options: [{ label: "90°", correct: true }, { label: "180°", trap: "Взял дугу вместо половины дуги" }, { label: "45°" }] },
  ],
  trig: [
    { id: "m-tr4", text: "cos 60° = ?", options: [{ label: "1/2", correct: true }, { label: "√3/2", trap: "Перепутал с sin 60°" }, { label: "1" }] },
    { id: "m-tr5", text: "tan 45° = ?", options: [{ label: "1", correct: true }, { label: "√2/2", trap: "Взял sin 45° вместо тангенса" }, { label: "0" }] },
    { id: "m-tr6", text: "sin²x + cos²x = ?", options: [{ label: "1", correct: true }, { label: "0" }, { label: "2", trap: "Сложил максимумы функций" }] },
  ],
  reduction: [
    { id: "m-rd4", text: "sin(180° − 30°) = ?", options: [{ label: "1/2", correct: true }, { label: "−1/2", trap: "Синус во II четверти положителен" }, { label: "√3/2" }] },
    { id: "m-rd5", text: "cos(360° − 60°) = ?", options: [{ label: "1/2", correct: true }, { label: "−1/2", trap: "Косинус в IV четверти положителен" }, { label: "−√3/2" }] },
    { id: "m-rd6", text: "Когда функция меняется на «ко-функцию»?", options: [{ label: "При 90° и 270°", correct: true }, { label: "При 180° и 360°", trap: "Перепутал правило смены функции" }, { label: "Всегда" }] },
  ],
};

/** Every check for a topic: the original pool first, then the added ones; a mock test takes them all */
export const checksFor = (skillId: string): Task[] => [
  ...(CHECKS[skillId] ?? []),
  ...(MORE_CHECKS[skillId] ?? []),
  ...(MOCK_CHECKS[skillId] ?? []),
  ...(MOCK_MORE[skillId] ?? []),
  ...(ENT_CHECKS[skillId] ?? []),
];
