"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "../choice/Icon";
import { CHECKS, daysBetween, EXAMS, formatDate, setById, skillById, STATE_LABEL, TODAY, type ExamId } from "./prepData";
import { ASSISTANT_PROMPTS, assistantReply } from "./prepAssistant";
import { answerTask, closed, proposedSet, type AnswerResult, type PrepModel, type PrepSub, type PrepTab } from "./prepModel";
import { StateGlyph } from "./SkillGraph";
import styles from "./prep.module.css";

type Props = {
  model: PrepModel;
  sub: PrepSub;
  onModel: (model: PrepModel) => void;
  onAccept: (setId: string) => void;
  /** Jump to another tab, optionally straight to one of its sub-tabs */
  onGo: (tab: PrepTab, sub?: PrepSub, exam?: ExamId) => void;
  onToast: (text: string) => void;
};

type ChatLine = { id: number; role: "student" | "assistant"; text: string };

/**
 * §4.4–4.5 — work on the current set. The set stays on screen as context; the sub-tab decides what fills
 * the rest: «Проверь себя», where answers prove a skill and colour it on the map, or the assistant,
 * which plans the preparation around the student's dates.
 */
export function CurrentSet({ model, sub, onModel, onAccept, onGo, onToast }: Props) {
  const set = model.currentSet ? setById(model.currentSet) : null;
  const [topic, setTopic] = useState<string | null>(set?.skills[0] ?? null);

  useEffect(() => {
    if (set && (!topic || !set.skills.includes(topic))) setTopic(set.skills[0]);
  }, [set, topic]);

  // The assistant plans the whole preparation, so it does not need a set to be in work
  const assistant = sub === "assistant";

  if (!set && !assistant) {
    const next = proposedSet(model);
    return (
      <div className={styles.emptyCanvas}>
        <h3>Текущего сета нет</h3>
        {next ? (
          <>
            <p className={styles.muted}>
              Система предлагает сет {next.number} «{next.title}» ({EXAMS[next.exam].name}) до {formatDate(next.deadline)}. {next.why}.
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

  const left = set ? daysBetween(TODAY, set.deadline) : 0;
  const skill = topic ? skillById(topic) : null;

  return (
    <div className={styles.setWork} data-mode={assistant ? "assistant" : "check"}>
      {set && (
        <section className={`${styles.canvas} ${styles.setHeader}`} aria-label="Текущий сет">
          <div>
            <p className={styles.eyebrow}>
              Сет {set.number} · {EXAMS[set.exam].name}
            </p>
            <h3 className={styles.setTitle}>{set.title}</h3>
            <p className={styles.muted}>
              до {formatDate(set.deadline)} · {left >= 0 ? `осталось ${left} дн.` : `просрочен на ${-left} дн. — прогноз пересчитан`} · порядок
              свободный
            </p>
          </div>
          <div className={styles.setProgress}>
            <span>
              доказано <strong>{closed(model, set)}</strong> из {set.skills.length}
            </span>
            <div className={styles.segments}>
              {set.skills.map((id) => (
                <span key={id} data-state={model.states[id]} title={`${skillById(id).name}: ${STATE_LABEL[model.states[id]]}`} />
              ))}
            </div>
            <button type="button" className={styles.secondary} onClick={() => onGo("sets", "map", set.exam)}>
              <Icon name="network" size={16} /> На карте навыков
            </button>
          </div>
        </section>
      )}

      {!assistant && set && (
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
      )}

      {assistant ? (
        <AssistantChat model={model} fallbackExam={set?.exam ?? "sat"} />
      ) : (
        skill && <CheckCanvas key={skill.id} skillId={skill.id} model={model} onModel={onModel} onGo={onGo} onToast={onToast} />
      )}
    </div>
  );
}

/* ---------- Проверь себя: prove a skill, one question at a time ---------- */

function CheckCanvas({
  skillId,
  model,
  onModel,
  onGo,
  onToast,
}: {
  skillId: string;
  model: PrepModel;
  onModel: (m: PrepModel) => void;
  onGo: (tab: PrepTab, sub?: PrepSub, exam?: ExamId) => void;
  onToast: (t: string) => void;
}) {
  const skill = skillById(skillId);
  const pool = CHECKS[skillId] ?? [];
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<(AnswerResult & { choice: number }) | null>(null);

  const task = pool.length ? pool[index % pool.length] : null;

  const answer = (i: number) => {
    if (!task || result) return;
    const r = answerTask(model, skillId, task, i);
    setResult({ ...r, choice: i });
    onModel(r.model);
    if (r.setPassed) onToast(`Сет ${r.setPassed.number} доказан — отчёт и следующий сет в «Обзоре»`);
  };

  const state = result?.to ?? model.states[skillId];

  return (
    <section className={`${styles.canvas} ${styles.topicCanvas}`} aria-label={`Проверь себя · ${skill.name}`}>
      <header className={styles.canvasHead}>
        <h3>Проверь себя · {skill.name}</h3>
        <span className={styles.checkState} data-state={state}>
          <StateGlyph state={state} size={12} /> {STATE_LABEL[state]}
        </span>
      </header>

      {task ? (
        <div className={styles.task}>
          <p className={styles.eyebrow}>Вопрос {(index % pool.length) + 1} из {pool.length} · демо</p>
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
                На карте навыков: «{skill.name}» — {STATE_LABEL[result.to]}
                {result.from !== result.to && ` (было: ${STATE_LABEL[result.from]})`}
              </p>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.primary}
                  onClick={() => {
                    setResult(null);
                    setIndex((i) => i + 1);
                  }}
                >
                  Ещё вопрос
                </button>
                <button type="button" className={styles.secondary} onClick={() => onGo("sets", "map", skill.exam)}>
                  <Icon name="network" size={16} /> Открыть карту
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className={styles.muted}>Вопросы по этому навыку появятся, когда до него дойдёт маршрут.</p>
      )}
    </section>
  );
}

/* ---------- Ассистент: plans the preparation, does not teach ---------- */

function AssistantChat({ model, fallbackExam }: { model: PrepModel; fallbackExam: ExamId }) {
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [input, setInput] = useState("");
  const idRef = useRef(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [lines]);

  const ask = (raw: string) => {
    const text = raw.trim();
    if (!text) return;
    setInput("");
    const reply = assistantReply(text, model, fallbackExam);
    setLines((l) => [...l, { id: ++idRef.current, role: "student", text }]);
    setTimeout(() => setLines((l) => [...l, { id: ++idRef.current, role: "assistant", text: reply }]), 600);
  };

  return (
    <section className={`${styles.canvas} ${styles.chatCanvas}`} aria-label="Ассистент подготовки">
      <header className={styles.canvasHead}>
        <h3>
          <Icon name="message-circle" size={18} /> Ассистент
        </h3>
        <span className={styles.muted}>план к твоим срокам, без уроков</span>
      </header>
      <div className={styles.chatLines} ref={listRef} aria-live="polite">
        {lines.length === 0 && (
          <div className={styles.assistantEmpty}>
            <p className={styles.muted}>
              Спроси, как успеть к своей дате: я разложу сеты по дням и скажу, сколько заниматься. Проверить знания — в «Проверь себя».
            </p>
            <div className={styles.promptChips}>
              {ASSISTANT_PROMPTS.map((p) => (
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
      </div>
      <form
        className={styles.chatForm}
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Например: у меня IELTS 12 декабря, как успеть?"
          aria-label="Сообщение ассистенту"
        />
        <button type="submit" className={styles.primary} disabled={!input.trim()}>
          Отправить
        </button>
      </form>
    </section>
  );
}
