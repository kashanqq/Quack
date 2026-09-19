// Обязательный входной мок-тест для новых пользователей (8 вопросов)
// Калибрует начальную модель знаний, выявляет корни и типичные ловушки по ключевым темам.

import type { SkillState } from "./prepData";

export type DiagnosticQuestion = {
  id: string;
  skillId: string;
  skillName: string;
  area: string;
  question: string;
  options: {
    label: string;
    key?: string;
    correct?: boolean;
    trap?: string;
  }[];
  explanation: string;
};

export const DIAGNOSTIC_8_QUESTIONS: DiagnosticQuestion[] = [
  {
    id: "d1",
    skillId: "linear",
    skillName: "Линейные уравнения",
    area: "Алгебра",
    question: "Решите уравнение: 3(x − 2) = 2x + 5",
    options: [
      { label: "x = 11", correct: true },
      { label: "x = 7", trap: "Забыл умножить вычитаемое на 3 при раскрытии скобок" },
      { label: "x = 1" },
      { label: "x = −1", trap: "Ошибка знака при переносе через знак равенства" },
    ],
    explanation: "Раскрываем скобки: 3x − 6 = 2x + 5. Переносим слагаемые: 3x − 2x = 5 + 6, получаем x = 11.",
  },
  {
    id: "d2",
    skillId: "quadratics",
    skillName: "Квадратичные функции",
    area: "Продвинутая математика",
    question: "Найдите корни квадратного уравнения: x² − 5x + 6 = 0",
    options: [
      { label: "x = 2 и x = 3", correct: true },
      { label: "x = −2 и x = −3", trap: "Перепутал знаки корней по теореме Виета" },
      { label: "x = 1 и x = 6" },
      { label: "x = −1 и x = −6" },
    ],
    explanation: "По теореме Виета: x₁ + x₂ = 5, x₁ · x₂ = 6. Корни: 2 и 3, так как (x − 2)(x − 3) = 0.",
  },
  {
    id: "d3",
    skillId: "systems",
    skillName: "Системы уравнений",
    area: "Алгебра",
    question: "Дана система: x + y = 10 и x − y = 4. Чему равно значение y?",
    options: [
      { label: "y = 3", correct: true },
      { label: "y = 7", trap: "Нашёл значение x и забыл вычислить y" },
      { label: "y = 6" },
      { label: "y = 4" },
    ],
    explanation: "Вычитаем второе уравнение из первого: 2y = 6 → y = 3. (Если сложить, получим x = 7, но в вопросе требовалось найти y).",
  },
  {
    id: "d4",
    skillId: "abs",
    skillName: "Модуль и его раскрытие",
    area: "Алгебра",
    question: "Сколько различных действительных решений имеет уравнение |2x − 3| = 7?",
    options: [
      { label: "2 решения (5 и −2)", correct: true },
      { label: "1 решение (5)", trap: "Потерял отрицательную ветвь раскрытия модуля" },
      { label: "0 решений" },
      { label: "Бесконечно много" },
    ],
    explanation: "Модуль раскрывается на две ветви: 2x − 3 = 7 → x = 5, либо 2x − 3 = −7 → x = −2. Всего 2 решения.",
  },
  {
    id: "d5",
    skillId: "inequalities",
    skillName: "Неравенства",
    area: "Алгебра",
    question: "Решите неравенство: −3x + 6 < 15",
    options: [
      { label: "x > −3", correct: true },
      { label: "x < −3", trap: "Не перевернул знак неравенства при делении на отрицательное число" },
      { label: "x > 3" },
      { label: "x < 3" },
    ],
    explanation: "−3x < 15 − 6 → −3x < 9. При делении на −3 знак неравенства меняется на противоположный: x > −3.",
  },
  {
    id: "d6",
    skillId: "circle",
    skillName: "Окружность и углы",
    area: "Геометрия",
    question: "Вписанный угол опирается на дугу окружности величиной 140°. Чему равен этот вписанный угол?",
    options: [
      { label: "70°", correct: true },
      { label: "140°", trap: "Взял величину дуги / центрального угла вместо вписанного" },
      { label: "280°" },
      { label: "90°" },
    ],
    explanation: "Вписанный угол равен половине дуги, на которую он опирается: 140° / 2 = 70°.",
  },
  {
    id: "d7",
    skillId: "triangles",
    skillName: "Подобие треугольников",
    area: "Геометрия",
    question: "Два треугольника подобны с коэффициентом k = 2. Площадь меньшего равна 6. Какова площадь большего треугольника?",
    options: [
      { label: "24", correct: true },
      { label: "12", trap: "Умножил площадь на k вместо k²" },
      { label: "18" },
      { label: "36" },
    ],
    explanation: "Площади подобных фигур относятся как квадрат коэффициента подобия: S₂ = S₁ · k² = 6 · 2² = 24.",
  },
  {
    id: "d8",
    skillId: "probability",
    skillName: "Анализ данных и вероятность",
    area: "Анализ данных",
    question: "В классе 25 учеников, 10 из них занимаются шахматами, среди шахматистов 4 девочки. Какова вероятность, что случайно выбранный шахматист — девочка?",
    options: [
      { label: "4 / 10 (или 2/5)", correct: true },
      { label: "4 / 25", trap: "Разделил на общее количество учеников вместо группы шахматистов" },
      { label: "6 / 10" },
      { label: "10 / 25" },
    ],
    explanation: "Вопрос звучит «выбранный шахматист — девочка», поэтому базой являются 10 шахматистов, а благоприятных исходов 4: P = 4/10.",
  },
];

export type DiagnosticResultSummary = {
  score: number;
  total: number;
  solidSkills: string[];
  attentionSkills: string[];
  trapsCaught: string[];
  statesUpdate: Record<string, SkillState>;
  words?: string;
};

export function evaluateDiagnostic(answers: Record<string, number>): DiagnosticResultSummary {
  let score = 0;
  const solidSkills: string[] = [];
  const attentionSkills: string[] = [];
  const trapsCaught: string[] = [];
  const statesUpdate: Record<string, SkillState> = {};

  DIAGNOSTIC_8_QUESTIONS.forEach((q) => {
    const selectedIndex = answers[q.id];
    if (selectedIndex === undefined) return;
    const option = q.options[selectedIndex];

    if (option.correct) {
      score += 1;
      solidSkills.push(q.skillName);
      statesUpdate[q.skillId] = "solid";
    } else {
      attentionSkills.push(q.skillName);
      statesUpdate[q.skillId] = "weak";
      if (option.trap) {
        trapsCaught.push(`${q.skillName}: ${option.trap}`);
      }
    }
  });

  return {
    score,
    total: DIAGNOSTIC_8_QUESTIONS.length,
    solidSkills,
    attentionSkills,
    trapsCaught,
    statesUpdate,
  };
}
