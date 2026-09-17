// All landing strings in one place. The landing ships in Russian; keeping the
// copy out of the markup means a second locale only needs another object of the
// same shape, not a rewrite of every component.
//
// Tone follows product-logic.md: "ты", no pressure, no scolding. Wordings are kept
// gender-neutral, because we never ask the student for a gender.

import type { Tempo } from "./PixelDuck";

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
      hint: "Крути глобус · нажми на точку или страну",
      loading: "Загружаем карту…",
      programsHere: "Есть в базе",
      noPrograms: "Программ в базе пока нет",
      back: "Отпустить",
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
