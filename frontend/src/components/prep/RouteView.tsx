"use client";

import type { ReactNode } from "react";
import { Icon } from "../choice/Icon";
import { EXAMS, formatShort, SETS, skillById, STATE_LABEL, type ExamId } from "./prepData";
import { closed, rankSets, setStatus, type PrepModel } from "./prepModel";
import styles from "./prep.module.css";

type Props = {
  exam: ExamId;
  switcher: ReactNode;
  model: PrepModel;
  onOpen: (setId: string) => void;
  onTake: (setId: string) => void;
};

/**
 * §4.3 — the route: the sets the assistant built for this student, in order. They are regenerated as
 * the student moves on, so there is no shop of ready sets and no route to compose by hand. The one thing
 * the student chooses is which set to work on: any open set can be taken instead of the one in work.
 */
export function RouteView({ exam, switcher, model, onOpen, onTake }: Props) {
  const sets = SETS.filter((s) => s.exam === exam);
  const inWork = SETS.find((s) => s.id === model.currentSet);
  // What the assistant would take next, if the student wants to switch
  const best = rankSets(model, exam).find((r) => r.set.id !== model.currentSet)?.set;
  const passed = sets.filter((s) => model.doneSets.includes(s.id)).length;

  return (
    <div className={styles.setList}>
      <header className={styles.setListHead}>
        <div>
          <h3>Маршрут</h3>
          <p className={styles.muted}>
            Сеты собраны под тебя и пересобираются по мере продвижения · пройдено {passed} из {sets.length}
          </p>
        </div>
        {switcher}
      </header>

      {inWork && inWork.exam !== exam && (
        <p className={styles.marketNote}>
          В работе сет по {EXAMS[inWork.exam].name}: «{inWork.title}». Возьмёшь сет здесь — он заменит его.
        </p>
      )}

      <ol className={styles.routeSteps}>
        {sets.map((set) => {
          const status = setStatus(model, set);
          const done = status === "done";
          const current = status === "current";
          return (
            <li key={set.id} data-done={done || undefined} data-here={current || undefined}>
              <span className={styles.routeMark} aria-hidden="true">
                {done ? <Icon name="check" size={14} /> : set.number}
              </span>
              <article className={styles.routeStep}>
                <div className={styles.routeStepHead}>
                  <strong>{set.title}</strong>
                  <span className={styles.muted}>
                    {formatShort(set.start)} – {formatShort(set.deadline)}
                  </span>
                </div>
                <span className={styles.routeStepMeta}>
                  <span className={styles.segments}>
                    {set.skills.map((id) => (
                      <span key={id} data-state={model.states[id]} title={`${skillById(id).name}: ${STATE_LABEL[model.states[id]]}`} />
                    ))}
                  </span>
                  доказано {closed(model, set)} из {set.skills.length}
                  {current && <b className={styles.routeNow}>в работе</b>}
                  {!current && set.id === best?.id && (
                    <b className={styles.fitTag}>
                      <Icon name="sparkles" size={12} /> ассистент советует
                    </b>
                  )}
                </span>
                {!done && (
                  <div className={styles.actions}>
                    {current ? (
                      <button type="button" className={styles.primary} onClick={() => onOpen(set.id)}>
                        Продолжить <Icon name="chevron-right" size={16} />
                      </button>
                    ) : (
                      <button type="button" className={styles.secondary} onClick={() => onTake(set.id)}>
                        {inWork ? "Сменить на этот" : "Взять в работу"}
                      </button>
                    )}
                    <button type="button" className={styles.link} onClick={() => onOpen(set.id)}>
                      Посмотреть →
                    </button>
                  </div>
                )}
              </article>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
