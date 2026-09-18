"use client";

import { useState, type ReactNode } from "react";
import { Icon } from "../choice/Icon";
import { formatShort, SETS, skillById, STATE_LABEL, type ExamId, type StudySet } from "./prepData";
import { closed, planFor, rankSets, setPlan, setStatus, type PrepModel } from "./prepModel";
import styles from "./prep.module.css";

type Props = {
  exam: ExamId;
  switcher: ReactNode;
  model: PrepModel;
  onModel: (model: PrepModel) => void;
  onOpen: (setId: string) => void;
  onTake: (setId: string) => void;
  onToast: (text: string) => void;
};

/**
 * §4.3 — the route is the student's own and optional. Without one, any set can be taken from «Все сеты».
 * «Составить маршрут» puts chosen sets ahead in the student's order; then the route shows where they are
 * on it and what is next.
 */
export function RouteView({ exam, switcher, model, onModel, onOpen, onTake, onToast }: Props) {
  const plan = planFor(model, exam);
  const [editing, setEditing] = useState(false);

  const save = (ids: string[]) => {
    onModel(setPlan(model, exam, ids));
    setEditing(false);
    onToast(ids.length ? `Маршрут сохранён: сетов ${ids.length}` : "Маршрут убран — сеты можно брать в любом порядке");
  };

  return (
    <div className={styles.setList}>
      <header className={styles.setListHead}>
        <div>
          <h3>Маршрут</h3>
          <p className={styles.muted}>Твой план, если он нужен. Над чем работать, решаешь ты — маршрут просто помогает не терять порядок.</p>
        </div>
        {switcher}
      </header>

      {editing ? (
        <RouteEditor key={exam} exam={exam} model={model} initial={plan.map((s) => s.id)} onSave={save} onCancel={() => setEditing(false)} />
      ) : plan.length === 0 ? (
        <section className={styles.routeEmpty}>
          <Icon name="route" size={28} className={styles.routeEmptyIcon} />
          <h4>Маршрута пока нет</h4>
          <p className={styles.muted}>
            Можно работать без него: бери любой сет в «Все сеты». Если удобнее идти по плану — выбери сеты и поставь их вперёд в том
            порядке, в каком хочешь пройти.
          </p>
          <button type="button" className={styles.primary} onClick={() => setEditing(true)}>
            <Icon name="plus" size={16} /> Составить маршрут
          </button>
        </section>
      ) : (
        <RoutePlan
          plan={plan}
          model={model}
          onOpen={onOpen}
          onTake={onTake}
          onEdit={() => setEditing(true)}
          onClear={() => save([])}
        />
      )}
    </div>
  );
}

/** The route as steps: passed ones ticked, the first open one is where the student is */
function RoutePlan({
  plan,
  model,
  onOpen,
  onTake,
  onEdit,
  onClear,
}: {
  plan: StudySet[];
  model: PrepModel;
  onOpen: (setId: string) => void;
  onTake: (setId: string) => void;
  onEdit: () => void;
  onClear: () => void;
}) {
  const next = plan.find((s) => !model.doneSets.includes(s.id));
  const passed = plan.filter((s) => model.doneSets.includes(s.id)).length;

  return (
    <>
      <div className={styles.routeBar}>
        <span className={styles.muted}>
          пройдено {passed} из {plan.length}
          {next ? ` · дальше сет ${next.number}` : " · маршрут пройден"}
        </span>
        <div className={styles.actions}>
          <button type="button" className={styles.secondary} onClick={onEdit}>
            <Icon name="pencil" size={15} /> Изменить маршрут
          </button>
          <button type="button" className={styles.link} onClick={onClear}>
            Убрать маршрут
          </button>
        </div>
      </div>

      <ol className={styles.routeSteps}>
        {plan.map((set, i) => {
          const status = setStatus(model, set);
          const done = status === "done";
          const here = set.id === next?.id;
          return (
            <li key={set.id} data-done={done || undefined} data-here={here || undefined}>
              <span className={styles.routeMark} aria-hidden="true">
                {done ? <Icon name="check" size={14} /> : i + 1}
              </span>
              <article className={styles.routeStep}>
                <div className={styles.routeStepHead}>
                  <strong>
                    Сет {set.number} · {set.title}
                  </strong>
                  <span className={styles.muted}>до {formatShort(set.deadline)}</span>
                </div>
                <span className={styles.routeStepMeta}>
                  <span className={styles.segments}>
                    {set.skills.map((id) => (
                      <span key={id} data-state={model.states[id]} title={`${skillById(id).name}: ${STATE_LABEL[model.states[id]]}`} />
                    ))}
                  </span>
                  доказано {closed(model, set)} из {set.skills.length}
                  {status === "current" && <b className={styles.routeNow}>в работе</b>}
                </span>
                {!done && (
                  <div className={styles.actions}>
                    {status === "current" ? (
                      <button type="button" className={styles.primary} onClick={() => onOpen(set.id)}>
                        Продолжить <Icon name="chevron-right" size={16} />
                      </button>
                    ) : (
                      <button type="button" className={here ? styles.primary : styles.secondary} onClick={() => onTake(set.id)}>
                        Взять в работу
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
    </>
  );
}

/** Pick the sets and their order: add from the rest, move up and down, take out */
function RouteEditor({
  exam,
  model,
  initial,
  onSave,
  onCancel,
}: {
  exam: ExamId;
  model: PrepModel;
  initial: string[];
  onSave: (ids: string[]) => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState<string[]>(initial);
  const open = SETS.filter((s) => s.exam === exam && !model.doneSets.includes(s.id));
  // The rest in the assistant's order, so the likely next ones are at hand
  const rest = rankSets(model, exam)
    .map((r) => r.set)
    .filter((s) => !draft.includes(s.id));
  const set = (id: string) => SETS.find((s) => s.id === id)!;

  const move = (i: number, by: number) =>
    setDraft((d) => {
      const next = [...d];
      [next[i], next[i + by]] = [next[i + by], next[i]];
      return next;
    });

  return (
    <section className={styles.routeEditor} aria-label="Составить маршрут">
      <div className={styles.routeColumn}>
        <p className={styles.eyebrow}>Мой маршрут · по порядку</p>
        {draft.length === 0 ? (
          <p className={styles.routeHint}>Добавь сеты из списка — в том порядке, в каком хочешь их пройти.</p>
        ) : (
          <ol className={styles.routeDraft}>
            {draft.map((id, i) => (
              <li key={id}>
                <span className={styles.routeMark}>{i + 1}</span>
                <span className={styles.routeDraftTitle}>
                  Сет {set(id).number} · {set(id).title}
                </span>
                <span className={styles.routeTools}>
                  <button type="button" aria-label="Выше" disabled={i === 0} onClick={() => move(i, -1)}>
                    <Icon name="arrow-up" size={15} />
                  </button>
                  <button type="button" aria-label="Ниже" disabled={i === draft.length - 1} onClick={() => move(i, 1)}>
                    <Icon name="arrow-down" size={15} />
                  </button>
                  <button type="button" aria-label="Убрать из маршрута" onClick={() => setDraft((d) => d.filter((x) => x !== id))}>
                    <Icon name="x" size={15} />
                  </button>
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className={styles.routeColumn}>
        <div className={styles.routeColumnHead}>
          <p className={styles.eyebrow}>Остальные сеты</p>
          {rest.length > 0 && (
            <button type="button" className={styles.link} onClick={() => setDraft((d) => [...d, ...rest.map((s) => s.id)])}>
              Добавить все по совету ассистента
            </button>
          )}
        </div>
        {rest.length === 0 ? (
          <p className={styles.routeHint}>{open.length ? "Все открытые сеты уже в маршруте." : "Все сеты пройдены."}</p>
        ) : (
          <ul className={styles.routeDraft}>
            {rest.map((s) => (
              <li key={s.id}>
                <span className={styles.routeDraftTitle}>
                  Сет {s.number} · {s.title}
                  <span className={styles.muted}> · до {formatShort(s.deadline)}</span>
                </span>
                <button type="button" className={styles.routeAdd} onClick={() => setDraft((d) => [...d, s.id])}>
                  <Icon name="plus" size={14} /> В маршрут
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className={styles.routeEditorFoot}>
        <button type="button" className={styles.primary} disabled={!draft.length && !initial.length} onClick={() => onSave(draft)}>
          {draft.length || !initial.length ? "Сохранить маршрут" : "Сохранить без маршрута"}
        </button>
        <button type="button" className={styles.secondary} onClick={onCancel}>
          Отмена
        </button>
      </div>
    </section>
  );
}
