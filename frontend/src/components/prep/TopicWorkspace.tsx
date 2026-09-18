"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "../choice/Icon";
import { daysBetween, formatShort, skillById, STATE_LABEL, TODAY, type StudySet, type Task } from "./prepData";
import { TOPIC_PROMPTS, topicReply } from "./prepAssistant";
import { answerTask, MISCONCEPTION_LABEL, type PrepModel } from "./prepModel";
import { StateGlyph } from "./SkillGraph";
import { checksFor, TOPICS, type TopicContent } from "./topicContent";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  set: StudySet;
  skillId: string;
  /** The set's topics in order, to step between them without going back to the graph */
  order: string[];
  /** This topic's own deadline */
  plannedBy: Date;
  onBack: () => void;
  onTopic: (skillId: string) => void;
  onModel: (model: PrepModel) => void;
  onToast: (text: string) => void;
};

type Line = { id: number; role: "student" | "assistant"; text: string };

/**
 * A topic opened from the set's graph: the graph gives way to a chat with the assistant, which starts
 * with the topic's minimum, and a mock test beside it. A wrong answer can be taken straight to the chat.
 */
export function TopicWorkspace({ model, set, skillId, order, plannedBy, onBack, onTopic, onModel, onToast }: Props) {
  const skill = skillById(skillId);
  const state = model.states[skillId];
  const content = TOPICS[skillId];
  const index = order.indexOf(skillId);
  const left = daysBetween(TODAY, plannedBy);
  const behind = state !== "solid" && left < 0;
  // Phones show one pane at a time
  const [pane, setPane] = useState<"chat" | "test">("chat");

  const [lines, setLines] = useState<Line[]>([]);
  const [typing, setTyping] = useState(false);
  const idRef = useRef(0);

  const say = (question: string, reply: string) => {
    setLines((l) => [...l, { id: ++idRef.current, role: "student", text: question }]);
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      setLines((l) => [...l, { id: ++idRef.current, role: "assistant", text: reply }]);
    }, 650);
  };

  const ask = (text: string) => {
    if (!text.trim() || typing) return;
    say(text.trim(), topicReply(text, model, skillId, set, content));
  };

  const explain = (task: Task, choice: number) => {
    if (typing) return;
    setPane("chat");
    say(`Разбери вопрос: «${task.text}»`, explainTask(task, choice, content));
  };

  return (
    <div className={styles.topicWork}>
      <header className={styles.setBar}>
        <button type="button" className={styles.backLink} onClick={onBack} aria-label="К графу сета" title="К графу сета">
          <Icon name="arrow-left" size={18} />
        </button>
        <div className={styles.setBarTitle}>
          <h2>{skill.name}</h2>
          <span className={styles.muted}>
            Сет {set.number} · {set.title} · тема {index + 1} из {order.length}
          </span>
        </div>
        <div className={styles.setBarSide}>
          <span className={behind ? styles.warn : styles.muted}>
            до {formatShort(plannedBy)} ·{" "}
            {state === "solid" ? "держится" : behind ? `просрочена на ${-left} дн.` : `осталось ${left} дн.`}
          </span>
          <span className={styles.checkState} data-state={state}>
            <StateGlyph state={state} size={12} /> {STATE_LABEL[state]}
          </span>
        </div>
        {/* The other topics of the set, to move on without the graph */}
        <nav className={styles.topicSteps} aria-label="Темы сета">
          {order.map((id, i) => (
            <button key={id} type="button" aria-current={id === skillId} onClick={() => onTopic(id)} title={skillById(id).name}>
              <StateGlyph state={model.states[id]} size={10} />
              <span>
                {i + 1}. {skillById(id).name}
              </span>
            </button>
          ))}
        </nav>
      </header>

      <div className={styles.paneSwitch} role="tablist" aria-label="Что показать">
        <button type="button" role="tab" aria-selected={pane === "chat"} onClick={() => setPane("chat")}>
          <Icon name="message-circle" size={15} /> Чат
        </button>
        <button type="button" role="tab" aria-selected={pane === "test"} onClick={() => setPane("test")}>
          <Icon name="circle-check" size={15} /> Мок-тест
        </button>
      </div>

      <div className={styles.topicWorkStage} data-pane={pane}>
        <section className={`${styles.canvas} ${styles.chatPane}`} aria-label="Чат по теме">
          <Chat model={model} skillId={skillId} content={content} lines={lines} typing={typing} onAsk={ask} />
        </section>
        <aside className={`${styles.canvas} ${styles.mockPane}`} aria-label="Мок-тест">
          <MockTest model={model} skillId={skillId} onModel={onModel} onToast={onToast} onExplain={explain} />
        </aside>
      </div>
    </div>
  );
}

/** A wrong (or right) answer, taken apart: the correct option, the trap behind the pick, the rule */
function explainTask(task: Task, choice: number, content?: TopicContent) {
  const right = task.options.find((o) => o.correct);
  const picked = task.options[choice];
  const parts = [`Правильный ответ — «${right?.label ?? "—"}».`];
  if (picked && !picked.correct) {
    parts.push(picked.trap ? `Ты выбрал «${picked.label}»: ${picked.trap.toLowerCase()}.` : `Ты выбрал «${picked.label}» — это не сходится с условием.`);
  } else {
    parts.push("Ты ответил верно — закрепи, почему так.");
  }
  if (content) parts.push(`Правило: ${content.points[0].charAt(0).toLowerCase()}${content.points[0].slice(1)}.`);
  return parts.join(" ");
}

/* ---------- Chat: opens with the topic's minimum, then anything the student asks ---------- */

function Chat({
  model,
  skillId,
  content,
  lines,
  typing,
  onAsk,
}: {
  model: PrepModel;
  skillId: string;
  content?: TopicContent;
  lines: Line[];
  typing: boolean;
  onAsk: (text: string) => void;
}) {
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (lines.length) listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [lines, typing]);

  return (
    <div className={styles.topicChat}>
      <div className={styles.chatLines} ref={listRef} aria-live="polite">
        <Brief model={model} skillId={skillId} content={content} />
        {lines.map((l) => (
          <p key={l.id} className={styles.chatLine} data-role={l.role}>
            {l.text}
          </p>
        ))}
        {typing && (
          <p className={styles.chatLine} data-role="assistant" aria-label="Ассистент печатает">
            …
          </p>
        )}
      </div>

      <div className={styles.promptChips}>
        {TOPIC_PROMPTS.map((p) => (
          <button key={p} type="button" onClick={() => onAsk(p)} disabled={typing}>
            {p}
          </button>
        ))}
      </div>
      <form
        className={styles.chatForm}
        onSubmit={(e) => {
          e.preventDefault();
          onAsk(input);
          setInput("");
        }}
      >
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Спроси что угодно по теме…" aria-label="Вопрос ассистенту" />
        <button type="submit" className={styles.primary} disabled={!input.trim() || typing}>
          Отправить
        </button>
      </form>
    </div>
  );
}

/** The assistant's first message: just enough to know what the topic is about */
function Brief({ model, skillId, content }: { model: PrepModel; skillId: string; content?: TopicContent }) {
  const [shown, setShown] = useState(false);
  const own = model.misconceptions[skillId].filter((m) => m.status !== "disputed");

  if (!content) {
    return (
      <div className={styles.topicBrief}>
        <p>Материал по этой теме появится, когда до неё дойдёт маршрут. Пока можно спросить меня о чём угодно.</p>
      </div>
    );
  }

  return (
    <div className={styles.topicBrief}>
      <p className={styles.eyebrow}>Коротко о теме</p>
      <p>{content.summary}</p>

      <p className={styles.eyebrow}>Нужно уметь</p>
      <ul className={styles.materialPoints}>
        {content.points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>

      <p className={styles.eyebrow}>Пример</p>
      <div className={styles.example}>
        <p>{content.example.q}</p>
        {shown ? (
          <p className={styles.exampleAnswer}>{content.example.a}</p>
        ) : (
          <button type="button" className={styles.link} onClick={() => setShown(true)}>
            Показать решение
          </button>
        )}
      </div>

      <p className={styles.eyebrow}>Где ошибаются</p>
      <ul className={styles.plainList}>
        {own.map((m) => (
          <li key={m.id} className={styles.misconception} data-status={m.status}>
            <span>{m.text}</span>
            <span className={styles.muted}>у тебя: {MISCONCEPTION_LABEL(m)}</span>
          </li>
        ))}
        <li className={styles.misconception}>
          <span>{content.trap}</span>
          <span className={styles.muted}>частая у всех</span>
        </li>
      </ul>
      <p className={styles.note}>Минимум для понимания, не курс. Спрашивай ниже, а когда будешь готов — мок-тест справа.</p>
    </div>
  );
}

/* ---------- Mock test: every question of the topic in a row, each answer moves the graph ---------- */

function MockTest({
  model,
  skillId,
  onModel,
  onToast,
  onExplain,
}: {
  model: PrepModel;
  skillId: string;
  onModel: (m: PrepModel) => void;
  onToast: (t: string) => void;
  onExplain: (task: Task, choice: number) => void;
}) {
  const pool = checksFor(skillId);
  const [round, setRound] = useState(0);
  const [picks, setPicks] = useState<number[]>([]);
  const [startState, setStartState] = useState(model.states[skillId]);
  // After an answer the question stays on screen until «Дальше»
  const [shownAt, setShownAt] = useState(0);
  const task = pool[shownAt];
  const pick = picks[shownAt];
  const finished = shownAt >= pool.length;
  const correct = picks.filter((p, i) => pool[i].options[p]?.correct).length;
  const state = model.states[skillId];

  if (!pool.length) return <p className={styles.muted}>Вопросы по этой теме появятся, когда до неё дойдёт маршрут.</p>;

  const answer = (i: number) => {
    if (pick !== undefined) return;
    const r = answerTask(model, skillId, pool[shownAt], i);
    setPicks((p) => [...p, i]);
    onModel(r.model);
    if (r.setPassed) onToast(`Сет ${r.setPassed.number} доказан целиком — отчёт в «Обзоре»`);
  };

  const restart = () => {
    setPicks([]);
    setShownAt(0);
    setStartState(model.states[skillId]);
    setRound((n) => n + 1);
  };

  return (
    <div className={styles.mockTest} key={round}>
      <header className={styles.mockHead}>
        <div>
          <p className={styles.eyebrow}>Мок-тест · демо</p>
          <h3>{finished ? "Итог" : `Вопрос ${shownAt + 1} из ${pool.length}`}</h3>
        </div>
        <span className={styles.mockDots} aria-hidden="true">
          {pool.map((t, i) => (
            <span
              key={t.id}
              data-result={
                picks[i] === undefined ? (i === shownAt ? "current" : undefined) : t.options[picks[i]]?.correct ? "correct" : "wrong"
              }
            />
          ))}
        </span>
      </header>

      {finished ? (
        <div className={styles.mockResult}>
          <p className={styles.mockScore}>
            <strong>{correct}</strong> из {pool.length}
          </p>
          <p className={styles.modelUpdate}>
            <StateGlyph state={state} size={12} />
            На графе: {STATE_LABEL[state]}
            {startState !== state && ` (было: ${STATE_LABEL[startState]})`}
          </p>
          <ul className={styles.mockReview}>
            {pool.map((t, i) => {
              const ok = t.options[picks[i]]?.correct;
              return (
                <li key={t.id} data-correct={ok}>
                  <Icon name={ok ? "check" : "x"} size={14} />
                  <span>{t.text}</span>
                  {!ok && (
                    <button type="button" className={styles.link} onClick={() => onExplain(t, picks[i])}>
                      Разобрать
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
          <div className={styles.actions}>
            <button type="button" className={styles.primary} onClick={restart}>
              Пройти ещё раз
            </button>
          </div>
        </div>
      ) : (
        <div className={styles.task}>
          <p className={styles.taskText}>{task.text}</p>
          <div className={styles.options} role="group" aria-label="Варианты ответа">
            {task.options.map((o, i) => (
              <button
                key={o.label}
                type="button"
                className={styles.option}
                data-result={pick !== undefined ? (o.correct ? "correct" : pick === i ? "wrong" : undefined) : undefined}
                disabled={pick !== undefined}
                onClick={() => answer(i)}
              >
                <span className={styles.optionLetter}>{"ABCD"[i]}</span>
                {o.label}
              </button>
            ))}
          </div>

          {pick !== undefined && (
            <div className={styles.feedback} data-correct={Boolean(task.options[pick].correct)}>
              <strong>
                {task.options[pick].correct
                  ? "Верно — засчитано"
                  : task.options[pick].trap
                    ? `Ловушка: ${task.options[pick].trap!.toLowerCase()}`
                    : "Неверно"}
              </strong>
              <div className={styles.actions}>
                <button type="button" className={styles.primary} onClick={() => setShownAt((n) => n + 1)}>
                  {shownAt + 1 < pool.length ? "Дальше" : "Итог"}
                </button>
                <button type="button" className={styles.secondary} onClick={() => onExplain(task, pick)}>
                  <Icon name="message-circle" size={15} /> Разобрать в чате
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
