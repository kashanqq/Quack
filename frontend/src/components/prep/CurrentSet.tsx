"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "../choice/Icon";
import { daysBetween, formatDate, GUIDELINES, setById, skillById, STATE_LABEL, TODAY } from "./prepData";
import {
  answerTask,
  closed,
  MISCONCEPTION_LABEL,
  proposedSet,
  type AnswerResult,
  type PrepModel,
  type PrepSub,
  type PrepTab,
} from "./prepModel";
import { StateGlyph } from "./SkillGraph";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  sub: PrepSub;
  onModel: (model: PrepModel) => void;
  onAccept: (setId: string) => void;
  /** Jump to another tab, optionally straight to one of its sub-tabs */
  onGo: (tab: PrepTab, sub?: PrepSub) => void;
  onToast: (text: string) => void;
};

type ChatLine = { id: number; role: "student" | "tutor" | "system"; text: string; detail?: string };

/**
 * §4.4–4.5 — work on the current set. The set and its topics stay on screen as context; the
 * sub-tabs decide what fills the right pane: the guideline, the tasks, or the tutor.
 */
export function CurrentSet({ model, sub, onModel, onAccept, onGo, onToast }: Props) {
  const set = model.currentSet ? setById(model.currentSet) : null;
  const [topic, setTopic] = useState<string | null>(set?.skills[0] ?? null);

  useEffect(() => {
    if (set && (!topic || !set.skills.includes(topic))) setTopic(set.skills[0]);
  }, [set, topic]);

  if (!set) {
    const next = proposedSet(model);
    return (
      <div className={styles.emptyCanvas}>
        <h3>Текущего сета нет</h3>
        {next ? (
          <>
            <p className={styles.muted}>
              Система предлагает сет {next.number} «{next.title}» до {formatDate(next.deadline)}. {next.why}.
            </p>
            <div className={styles.actions}>
              <button type="button" className={styles.primary} onClick={() => onAccept(next.id)}>
                Принять сет {next.number}
              </button>
              <button type="button" className={styles.secondary} onClick={() => onGo("sets")}>
                Выбрать другой
              </button>
            </div>
          </>
        ) : (
          <p className={styles.muted}>Все сеты пройдены.</p>
        )}
      </div>
    );
  }

  const left = daysBetween(TODAY, set.deadline);
  const skill = topic ? skillById(topic) : null;

  return (
    <div className={styles.setWork}>
      <section className={`${styles.canvas} ${styles.setHeader}`} aria-label="Текущий сет">
        <div>
          <p className={styles.eyebrow}>Сет {set.number} · SAT Math</p>
          <h3 className={styles.setTitle}>{set.title}</h3>
          <p className={styles.muted}>
            до {formatDate(set.deadline)} · {left >= 0 ? `осталось ${left} дн.` : `просрочен на ${-left} дн. — прогноз пересчитан`} · порядок
            свободный
          </p>
        </div>
        <div className={styles.setProgress}>
          <span>
            закрыто <strong>{closed(model, set)}</strong> из {set.skills.length}
          </span>
          <div className={styles.segments}>
            {set.skills.map((id) => (
              <span key={id} data-state={model.states[id]} title={`${skillById(id).name}: ${STATE_LABEL[model.states[id]]}`} />
            ))}
          </div>
          <button
            type="button"
            className={styles.secondary}
            onClick={() => onToast(`Соберём мок по сету: 8–12 заданий по ${set.skills.length} топикам, которых ты не видел`)}
          >
            <Icon name="play" size={16} /> Мок по сету
          </button>
        </div>
      </section>

      <nav className={`${styles.canvas} ${styles.topics}`} aria-label="Топики">
        <p className={styles.eyebrow}>Топики</p>
        {set.skills.map((id) => {
          const s = skillById(id);
          const active = model.misconceptions[id].filter((m) => m.status === "confirmed" || m.status === "suspected");
          return (
            <button key={id} type="button" className={styles.topic} aria-current={topic === id} onClick={() => setTopic(id)}>
              <StateGlyph state={model.states[id]} />
              <span className={styles.topicText}>
                <span>{s.name}</span>
                <span className={styles.muted}>
                  {STATE_LABEL[model.states[id]]}
                  {s.root && " · корень"}
                  {active.length > 0 && " · ловушка"}
                </span>
              </span>
            </button>
          );
        })}
      </nav>

      {skill &&
        (sub === "tutor" ? (
          <PrepChat key={`chat-${set.id}`} topicName={skill.name} topicId={skill.id} setTitle={set.title} model={model} />
        ) : sub === "tasks" ? (
          <TaskCanvas key={`task-${skill.id}`} skillId={skill.id} model={model} onModel={onModel} onToast={onToast} />
        ) : (
          <GuideCanvas key={`guide-${skill.id}`} skillId={skill.id} model={model} onGo={onGo} />
        ))}
    </div>
  );
}

/* ---------- Гайдлайн: what this topic asks of you ---------- */

function GuideCanvas({ skillId, model, onGo }: { skillId: string; model: PrepModel; onGo: (tab: PrepTab, sub?: PrepSub) => void }) {
  const skill = skillById(skillId);
  const guide = GUIDELINES[skillId];
  const traps = model.misconceptions[skillId].filter((m) => m.status !== "disputed");

  return (
    <section className={`${styles.canvas} ${styles.topicCanvas}`} aria-label={`Гайдлайн · ${skill.name}`}>
      <header className={styles.canvasHead}>
        <h3>{skill.name}</h3>
        <span className={styles.muted}>гайдлайн собран для тебя сейчас</span>
      </header>

      {guide ? (
        <>
          <div className={styles.guide}>
            <div>
              <p className={styles.eyebrow}>Как готовиться</p>
              <p>{guide.prepare}</p>
            </div>
            <div>
              <p className={styles.eyebrow}>Что нужно уметь</p>
              <ul className={styles.dotList}>
                {guide.mustKnow.map((k) => (
                  <li key={k}>{k}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className={styles.eyebrow}>Ловушки у тебя</p>
              {traps.length || guide.traps.length ? (
                <ul className={styles.dotList}>
                  {traps.map((m) => (
                    <li key={m.id}>
                      {m.text} <span className={styles.muted}>({MISCONCEPTION_LABEL(m)})</span>
                    </li>
                  ))}
                  {traps.length === 0 && guide.traps.map((t) => <li key={t}>{t}</li>)}
                </ul>
              ) : (
                <p className={styles.muted}>Пока не замечено</p>
              )}
            </div>
            <div>
              <p className={styles.eyebrow}>Что решать</p>
              <p>{guide.practice}</p>
            </div>
          </div>
          <div className={styles.actions}>
            <button type="button" className={styles.primary} onClick={() => onGo("current", "tasks")}>
              <Icon name="play" size={16} /> К задачам
            </button>
            <button type="button" className={styles.secondary} onClick={() => onGo("current", "tutor")}>
              <Icon name="message-circle" size={16} /> Спросить репетитора
            </button>
          </div>
        </>
      ) : (
        <p className={styles.muted}>Гайдлайн соберётся, когда подойдёшь к этому топику.</p>
      )}
    </section>
  );
}

/* ---------- Задачи: one task at a time, each answer moves the model ---------- */

function TaskCanvas({
  skillId,
  model,
  onModel,
  onToast,
}: {
  skillId: string;
  model: PrepModel;
  onModel: (m: PrepModel) => void;
  onToast: (t: string) => void;
}) {
  const skill = skillById(skillId);
  const guide = GUIDELINES[skillId];
  const [taskIndex, setTaskIndex] = useState(0);
  const [result, setResult] = useState<(AnswerResult & { choice: number }) | null>(null);

  const task = guide?.tasks[taskIndex % guide.tasks.length];

  const answer = (i: number) => {
    if (!task || result) return;
    const r = answerTask(model, skillId, task, i);
    setResult({ ...r, choice: i });
    onModel(r.model);
    if (r.setPassed) onToast(`Сет ${r.setPassed.number} пройден — отчёт и следующий сет в Обзоре`);
  };

  return (
    <section className={`${styles.canvas} ${styles.topicCanvas}`} aria-label={`Задачи · ${skill.name}`}>
      <header className={styles.canvasHead}>
        <h3>{skill.name}</h3>
        <span className={styles.muted}>{STATE_LABEL[model.states[skillId]]}</span>
      </header>

      {guide && task ? (
        <div className={styles.task}>
          <p className={styles.eyebrow}>Задача {(taskIndex % guide.tasks.length) + 1} из пула · демо</p>
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
              <strong>{result.correct ? "Верно" : result.trap ? `Ловушка: ${result.trap.toLowerCase()}` : "Неверно"}</strong>
              <p>{task.explain}</p>
              <p className={styles.modelUpdate}>
                <Icon name="sparkles" size={14} />
                Модель знаний обновлена: {STATE_LABEL[result.from]}
                {result.from !== result.to && ` → ${STATE_LABEL[result.to]}`}
              </p>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.primary}
                  onClick={() => {
                    setResult(null);
                    setTaskIndex((i) => i + 1);
                  }}
                >
                  Следующая задача
                </button>
                <button
                  type="button"
                  className={styles.secondary}
                  onClick={() => onToast(`Мок по топику «${skill.name}»: 5–7 заданий одного навыка`)}
                >
                  Мок по топику
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className={styles.muted}>Задачи соберутся, когда подойдёшь к этому топику.</p>
      )}
    </section>
  );
}

function tutorReply(text: string, topicName: string, topicId: string, model: PrepModel): { text: string; detail?: string } {
  const t = text.toLowerCase();
  const guide = GUIDELINES[topicId];
  const confirmed = model.misconceptions[topicId].find((m) => m.status === "confirmed");
  if (/не понима|почему|объясни|как /.test(t)) {
    return {
      text: `Давай по шагам. Главное здесь: ${guide?.mustKnow[0].toLowerCase() ?? topicName.toLowerCase()}. Попробуй применить это в «Задачах» и напиши, что получилось.`,
    };
  }
  if (/\d/.test(t) && confirmed) {
    return {
      text: "Проверь ещё раз обе ветви — здесь легко потерять вторую. Что будет, если выражение под модулем отрицательное?",
      detail: `Свидетельство из чата (слабое): «${text}» → ${topicName}. В сет не пишется, пока не подтвердит задача.`,
    };
  }
  if (/задач|ещё|еще|дай/.test(t)) {
    return { text: `Держи: ${guide?.tasks[guide.tasks.length - 1].text ?? "задача появится, когда соберётся гайдлайн"}` };
  }
  return {
    text: `Понял. В «${topicName}» у тебя сейчас ${STATE_LABEL[model.states[topicId]]} — могу объяснить правило, разобрать твоё решение или дать задачу.`,
  };
}

/* ---------- Репетитор: questions about the topic or the whole set ---------- */

function PrepChat({ topicName, topicId, setTitle, model }: { topicName: string; topicId: string; setTitle: string; model: PrepModel }) {
  const [level, setLevel] = useState<"topic" | "set">("topic");
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [input, setInput] = useState("");
  const idRef = useRef(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [lines]);

  const send = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    const reply = tutorReply(text, level === "topic" ? topicName : setTitle, topicId, model);
    setLines((l) => [...l, { id: ++idRef.current, role: "student", text }]);
    setTimeout(() => setLines((l) => [...l, { id: ++idRef.current, role: "tutor", text: reply.text }]), 700);
    // The observer runs after the answer and never holds it up
    if (reply.detail) {
      setTimeout(
        () => setLines((l) => [...l, { id: ++idRef.current, role: "system", text: "Модель знаний обновлена", detail: reply.detail }]),
        2400
      );
    }
  };

  return (
    <section className={`${styles.canvas} ${styles.chatCanvas}`} aria-label="Чат подготовки">
      <header className={styles.canvasHead}>
        <h3>
          <Icon name="message-circle" size={18} /> Репетитор
        </h3>
        <div className={styles.segmented} role="tablist">
          <button type="button" role="tab" aria-selected={level === "topic"} onClick={() => setLevel("topic")}>
            Топик
          </button>
          <button type="button" role="tab" aria-selected={level === "set"} onClick={() => setLevel("set")}>
            Весь сет
          </button>
        </div>
      </header>
      <div className={styles.chatLines} ref={listRef} aria-live="polite">
        {lines.length === 0 && (
          <p className={styles.muted}>
            {level === "topic"
              ? `Спроси про «${topicName}», пришли решение или попроси задачу.`
              : `Вопросы поверх всего сета «${setTitle}».`}
          </p>
        )}
        {lines.map((l) =>
          l.role === "system" ? (
            <details key={l.id} className={styles.systemLine}>
              <summary>
                <Icon name="sparkles" size={14} /> {l.text}
              </summary>
              <p>{l.detail}</p>
            </details>
          ) : (
            <p key={l.id} className={styles.chatLine} data-role={l.role}>
              {l.text}
            </p>
          )
        )}
      </div>
      <form className={styles.chatForm} onSubmit={send}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={level === "topic" ? "Например: |x − 2| = 3, у меня x = 5" : "Вопрос по сету"}
          aria-label="Сообщение репетитору"
        />
        <button type="submit" className={styles.primary} disabled={!input.trim()}>
          Отправить
        </button>
      </form>
    </section>
  );
}
