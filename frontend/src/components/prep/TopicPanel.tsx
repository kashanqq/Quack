"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "../choice/Icon";
import { formatShort, skillById, STATE_LABEL, TODAY, type StudySet } from "./prepData";
import { TOPIC_PROMPTS, topicReply } from "./prepAssistant";
import { answerTask, MISCONCEPTION_LABEL, type AnswerResult, type PrepModel } from "./prepModel";
import { StateGlyph } from "./SkillGraph";
import { checksFor, TOPICS } from "./topicContent";
import styles from "./prep.module.css";

type Tab = "material" | "check" | "chat";

const TABS: { tab: Tab; label: string; icon: "book-open-check" | "circle-check" | "message-circle" }[] = [
  { tab: "material", label: "Материал", icon: "book-open-check" },
  { tab: "check", label: "Проверка", icon: "circle-check" },
  { tab: "chat", label: "Ассистент", icon: "message-circle" },
];

type Props = {
  model: PrepModel;
  set: StudySet;
  skillId: string;
  /** When this topic is planned to hold, from its place on the set's timeline */
  plannedBy: Date;
  onModel: (model: PrepModel) => void;
  onToast: (text: string) => void;
  /** Hides the panel so the graph takes the whole width */
  onClose: () => void;
};

/**
 * One topic of a set: a minimal explanation, a short check that moves its state on the graph, and an
 * assistant to ask anything about it. Keyed by topic by the caller, so switching topics starts clean.
 */
export function TopicPanel({ model, set, skillId, plannedBy, onModel, onToast, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("material");
  const skill = skillById(skillId);
  const state = model.states[skillId];
  const behind = state !== "solid" && plannedBy < TODAY;

  return (
    <section className={`${styles.canvas} ${styles.topicPanel}`} aria-label={`Тема: ${skill.name}`}>
      <header className={styles.topicHead}>
        <div>
          <p className={styles.eyebrow}>
            Тема сета {set.number} · до {formatShort(plannedBy)}
            {behind && <span className={styles.behindTag}>отстаёт</span>}
          </p>
          <h3 className={styles.topicTitle}>{skill.name}</h3>
        </div>
        <div className={styles.topicHeadSide}>
          <span className={styles.checkState} data-state={state}>
            <StateGlyph state={state} size={12} /> {STATE_LABEL[state]}
          </span>
          <button type="button" className={styles.topicClose} aria-label="Закрыть тему" title="Закрыть" onClick={onClose}>
            <Icon name="x" size={16} />
          </button>
        </div>
      </header>

      <div className={styles.topicTabs} role="tablist" aria-label="Что внутри темы">
        {TABS.map((t) => (
          <button key={t.tab} type="button" role="tab" aria-selected={tab === t.tab} onClick={() => setTab(t.tab)}>
            <Icon name={t.icon} size={15} />
            {t.label}
          </button>
        ))}
      </div>

      <div className={styles.topicBody} key={tab}>
        {tab === "material" && <Material model={model} skillId={skillId} onCheck={() => setTab("check")} />}
        {tab === "check" && <Check model={model} skillId={skillId} onModel={onModel} onToast={onToast} />}
        {tab === "chat" && <TopicChat model={model} set={set} skillId={skillId} />}
      </div>
    </section>
  );
}

/* ---------- Материал: just enough to know what the topic is ---------- */

function Material({ model, skillId, onCheck }: { model: PrepModel; skillId: string; onCheck: () => void }) {
  const content = TOPICS[skillId];
  const [shown, setShown] = useState(false);
  const own = model.misconceptions[skillId].filter((m) => m.status !== "disputed");

  if (!content) return <p className={styles.muted}>Материал по этой теме появится, когда до неё дойдёт маршрут.</p>;

  return (
    <div className={styles.material}>
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

      <div className={styles.actions}>
        <button type="button" className={styles.primary} onClick={onCheck}>
          <Icon name="circle-check" size={16} /> Проверить себя
        </button>
      </div>
      <p className={styles.note}>Это минимум для понимания, а не курс. Демо-материал: позже его соберёт ассистент под тебя.</p>
    </div>
  );
}

/* ---------- Проверка: short questions, each answer is evidence ---------- */

function Check({
  model,
  skillId,
  onModel,
  onToast,
}: {
  model: PrepModel;
  skillId: string;
  onModel: (m: PrepModel) => void;
  onToast: (t: string) => void;
}) {
  const pool = checksFor(skillId);
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<(AnswerResult & { choice: number }) | null>(null);
  const task = pool.length ? pool[index % pool.length] : null;

  const answer = (i: number) => {
    if (!task || result) return;
    const r = answerTask(model, skillId, task, i);
    setResult({ ...r, choice: i });
    onModel(r.model);
    if (r.setPassed) onToast(`Сет ${r.setPassed.number} доказан целиком — отчёт в «Обзоре»`);
  };

  if (!task) return <p className={styles.muted}>Вопросы по этой теме появятся, когда до неё дойдёт маршрут.</p>;

  return (
    <div className={styles.task}>
      <p className={styles.eyebrow}>
        Вопрос {(index % pool.length) + 1} из {pool.length} · демо
      </p>
      <p className={styles.taskText}>{task.text}</p>
      <div className={styles.options} role="group" aria-label="Варианты ответа">
        {task.options.map((o, i) => (
          <button
            key={o.label}
            type="button"
            className={styles.option}
            data-result={result ? (o.correct ? "correct" : result.choice === i ? "wrong" : undefined) : undefined}
            disabled={Boolean(result)}
            onClick={() => answer(i)}
          >
            <span className={styles.optionLetter}>{"ABCD"[i]}</span>
            {o.label}
          </button>
        ))}
      </div>

      {result && (
        <div className={styles.feedback} data-correct={result.correct}>
          <strong>{result.correct ? "Верно — засчитано" : result.trap ? `Ловушка: ${result.trap.toLowerCase()}` : "Неверно"}</strong>
          <p className={styles.modelUpdate}>
            <StateGlyph state={result.to} size={12} />
            На графе: {STATE_LABEL[result.to]}
            {result.from !== result.to && ` (было: ${STATE_LABEL[result.from]})`}
          </p>
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.primary}
              onClick={() => {
                setResult(null);
                setIndex((n) => n + 1);
              }}
            >
              Ещё вопрос
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- Ассистент: ask anything about the topic ---------- */

type Line = { id: number; role: "student" | "assistant"; text: string };

function TopicChat({ model, set, skillId }: { model: PrepModel; set: StudySet; skillId: string }) {
  const [lines, setLines] = useState<Line[]>([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const idRef = useRef(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [lines, typing]);

  const ask = (raw: string) => {
    const text = raw.trim();
    if (!text || typing) return;
    setInput("");
    setLines((l) => [...l, { id: ++idRef.current, role: "student", text }]);
    setTyping(true);
    const reply = topicReply(text, model, skillId, set, TOPICS[skillId]);
    setTimeout(() => {
      setTyping(false);
      setLines((l) => [...l, { id: ++idRef.current, role: "assistant", text: reply }]);
    }, 650);
  };

  return (
    <div className={styles.topicChat}>
      <div className={styles.chatLines} ref={listRef} aria-live="polite">
        {lines.length === 0 && (
          <div className={styles.assistantEmpty}>
            <p className={styles.muted}>Спроси что угодно по теме «{skillById(skillId).name}»: объяснить проще, пример, где ты ошибаешься.</p>
            <div className={styles.promptChips}>
              {TOPIC_PROMPTS.map((p) => (
                <button key={p} type="button" onClick={() => ask(p)}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}
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
      <form
        className={styles.chatForm}
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
      >
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Спроси по теме…" aria-label="Вопрос ассистенту" />
        <button type="submit" className={styles.primary} disabled={!input.trim() || typing}>
          Отправить
        </button>
      </form>
    </div>
  );
}
