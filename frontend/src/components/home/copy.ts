// All landing strings in one place. The landing ships in Russian; keeping the
// copy out of the markup means a second locale only needs another object of the
// same shape, not a rewrite of every component.
//
// Tone follows product-logic.md: "ты", no pressure, no scolding. Wordings are kept
// gender-neutral, because we never ask the student for a gender.

import type { Tempo } from "@/components/duck/PixelDuck";

export const copy = {
  nav: {
    possibilities: "Возможности",
    preparation: "Подготовка",
    choice: "Выбор",
    resources: "Ресурсы",
    howItWorks: "Как это работает?",
    about: "О нас",
    pricing: "Подписки",
    login: "Войти",
    signup: "Регистрация",
  },

  footer: {
    tagline: "Твой личный помощник для поступления в правильный университет.",
    product: "Продукт",
    company: "Ресурсы",
    account: "Аккаунт",
    rights: "© 2026 Quack! Все права защищены.",
    toTop: "Наверх",
  },

  // Prices are a draft: nothing in product-logic.md fixes plans or amounts yet.
  pricing: {
    heading: "Выбери подписку",
    lead: "Начать можно бесплатно. Отменить подписку — в любой момент, без вопросов.",
    monthly: "Ежемесячно",
    yearly: "Ежегодно",
    yearlyNote: "−20% при оплате за год",
    perMonth: "₸ / мес",
    billedYearly: "при оплате за год",
    recommended: "Рекомендуем",
    featuresTitle: "Что входит",
    plans: [
      {
        id: "start",
        name: "Старт",
        blurb: "Разобраться, куда поступать, и понять, чего не хватает.",
        monthly: 0,
        yearly: 0,
        cta: "Начать бесплатно",
        features: [
          "Профиль и чат подбора",
          "Подборка программ с оценкой реалистичности",
          "Сравнение программ",
          "До 5 сохранённых программ",
          "Первичный замер знаний",
        ],
      },
      {
        id: "pro",
        name: "Pro",
        blurb: "Весь путь до экзамена: план, сеты и репетитор под твой темп.",
        monthly: 4990,
        yearly: 3990,
        cta: "Оформить Pro",
        recommended: true,
        features: [
          "Всё из «Старт»",
          "Без лимита на сохранённые программы",
          "Сеты подготовки под твои требования и темп",
          "Чат подготовки — репетитор, который помнит твои ошибки",
          "Вехи и напоминания о дедлайнах",
          "План сам перестраивается, когда что-то меняется",
        ],
      },
    ] as {
      id: string;
      name: string;
      blurb: string;
      monthly: number;
      yearly: number;
      cta: string;
      recommended?: boolean;
      features: string[];
    }[],
  },

  hero: {
    cta: "Стартуем!",
    subtitleBefore: "Твой личный помощник для нахождения ",
    subtitleAccent: "правильного университета",
    subtitleAfter: " именно для тебя.",
    scrollHint: "листай вниз",
  },

  // Roadmap nodes: the student's journey from product-logic.md
  roadmap: {
    profile: "Анкета",
    programs: "Программы",
    plan: "План",
    sets: "Наборы",
    exam: "Экзамен",
  },

  quack: {
    heading: "Quack?",
    tabs: {
      uni: "Выбор университета",
      chat: "Подготовка с ассистентом",
      tempo: "Свой темп",
    },

    globe: {
      label: "Глобус с университетами из базы",
      hint: "Крути глобус · нажми на подсвеченную страну — там есть университеты",
      loading: "Загружаем карту…",
      programsHere: "Есть в базе",
      noPrograms: "Программ в базе пока нет",
      back: "Отпустить",
      deadline: "дедлайн",
    },

    uni: {
      caption: "Подборка под твой профиль",
      demo: "демо",
      admission: "Вступительные",
      cost: "Стоимость",
      deadline: "Дедлайн",
      fits: "Кому подойдёт",
      perYear: "/год",
      pick: "Показать программу",
    },

    chat: {
      caption: "Ассистент помнит, где ты остановился",
      typing: "печатает",
      you: "ты",
      bot: "Quack",
    },

    tempo: {
      heading: "Выбирай свой темп",
      footer: "Под своё состояние!",
      caption: "Темп можно поменять в любой день — пропуски никто не считает",
      ducks: [
        { tempo: "fast", name: "Спринт", note: "3–4 сета в день" },
        { tempo: "steady", name: "Ровный шаг", note: "сет в день, без рывков" },
        { tempo: "chill", name: "На чиле", note: "пара сетов в неделю" },
      ] as { tempo: Tempo; name: string; note: string }[],
    },
  },

  layers: {
    heading: "Под основой",
    lead: "Шесть слоёв, из которых собран Quack!: листай — и они раскроются по одному.",
    items: [
      {
        name: "Клиент",
        tagline: "Студенческий интерфейс и чат",
        text: "Минималистичный интерфейс для интерактивного обучения и общения.",
      },
      {
        name: "Оркестрация",
        tagline: "API и маршрутизация",
        text: "Управляет вызовами API и координирует запросы в масштабах всей системы.",
      },
      {
        name: "Слой ИИ",
        tagline: "Понимание и объяснение",
        text: "Интерпретирует естественный язык и генерирует образовательные пояснения.",
      },
      {
        name: "Система правил",
        tagline: "Детерминированный журнал",
        text: "Применяет фиксированные правила для точной оценки и проверки логики.",
      },
      {
        name: "Данные и хранение",
        tagline: "Граф знаний и кэш",
        text: "Сохраняет и связывает концептуальные узлы, храня состояние системы и кэш.",
      },
      {
        name: "Внешние источники",
        tagline: "Поиск в интернете и LLM API",
        text: "Получает дополнительную информацию и использует мощные базовые модели.",
        tags: ["Web Search API", "LLM API", "External KBs", "Library Systems"],
      },
    ] as { name: string; tagline: string; text: string; tags?: string[] }[],
  },
} as const;

export type ChatTurn = { from: "bot" | "you"; text: string };

/** Demo dialogues for the landing. Illustrative, not real assistant output. */
export const DIALOGUES: ChatTurn[][] = [
  [
    { from: "bot", text: "Занимаемся сегодня?" },
    { from: "you", text: "Конечно, хочу начать с SAT" },
    { from: "bot", text: "Будет сделано! *quack*" },
  ],
  [
    { from: "you", text: "Хочу в Европу, но бюджет до €4000 в год" },
    { from: "bot", text: "Отмечаю в профиле. Под это подходят 4 программы — показать?" },
  ],
  [
    { from: "you", text: "Успею подготовиться к марту?" },
    { from: "bot", text: "Если брать по 3 сета в неделю — да." },
    { from: "bot", text: "Могу собрать план прямо сейчас." },
  ],
  [
    { from: "you", text: "Что подтянуть в первую очередь?" },
    { from: "bot", text: "Слабее всего сейчас математика." },
    { from: "bot", text: "Начнём с неё — по 20 минут в день." },
  ],
];
