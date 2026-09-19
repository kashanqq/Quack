"use client";

import { useState, type ReactNode } from "react";
import { Icon } from "../choice/Icon";
import {
  formatShort,
  SETS,
  skillById,
  STATE_LABEL,
  type ExamId,
  type StudySet,
} from "./prepData";
import { closed, rankSets, setStatus, type PrepModel } from "./prepModel";
import { StateGlyph } from "./SkillGraph";
import { TOPICS } from "./topicContent";
import styles from "./prep.module.css";

type Props = {
  exam: ExamId;
  switcher: ReactNode;
  model: PrepModel;
  onOpen: (setId: string, topic?: string) => void;
  onTake: (setId: string) => void;
  onOpenDiagnostic?: () => void;
};

/**
 * §4.3 — Маршрут: каталог и плиточный селектор сетов.
 * В дефолтном виде карточки компактны, подробная информация раскрывается ТОЛЬКО у одного
 * выбранного/наведённого сета, соседние плитки не растягиваются и не меняют высоту.
 * Кнопки выбора сета соединены в стильный низкоконтрастный блок.
 */
export function RouteView({ exam, switcher, model, onOpen, onTake, onOpenDiagnostic }: Props) {
  const sets = SETS.filter((s) => s.exam === exam);
  const best = rankSets(model, exam).find((r) => r.set.id !== model.currentSet)?.set;
  const passed = sets.filter((s) => model.doneSets.includes(s.id)).length;

  // Строгая изоляция: одновременно развёрнут строго максимум ОДИН сет
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [pinnedId, setPinnedId] = useState<string | null>(null);

  const activeOpenId = hoveredId ?? pinnedId;

  return (
    <div className={styles.setList}>
      <header className={styles.setListHead}>
        <div>
          <h3>Маршрут подготовки</h3>
          <p className={styles.muted}>
            Выбери активный сет · в работе ровно 1 сет · сменить можно в любой момент · пройдено {passed} из {sets.length}
          </p>
        </div>
        {switcher}
      </header>

      {/* Обязательный входной замер для новых пользователей (прототип 8 вопросов) */}
      {onOpenDiagnostic && (
        <div className={styles.routeDiagnosticBar}>
          <div className={styles.routeDiagnosticInfo}>
            <span className={styles.diagnosticTag}>
              <Icon name="sparkles" size={12} /> {model.diagnosticDone ? "Входной замер пройден" : "Обязательный замер"}
            </span>
            <span className={styles.routeDiagnosticSub}>
              {model.diagnosticDone
                ? "Маршрут откалиброван по 8 ключевым темам. Можно пересдать замер для повторной калибровки."
                : "Входной мок-тест на 8 вопросов для новых пользователей: откалибрует модель знаний и порядок сетов."}
            </span>
          </div>
          <button
            type="button"
            className={styles.routeDiagnosticBtn}
            onClick={onOpenDiagnostic}
          >
            <Icon name="sparkles" size={13} />
            {model.diagnosticDone ? "Пересдать замер (8 вопр.)" : "Пройти замер (8 вопр.)"}
          </button>
        </div>
      )}

      {/* Плиточная сетка сетов */}
      <div className={styles.routeTilesGrid} role="region" aria-label="Сетка сетов">
        {sets.map((set) => {
          const status = setStatus(model, set);
          const isCurrent = model.currentSet === set.id;
          const isDone = status === "done";
          const isBest = set.id === best?.id;
          const closedCount = closed(model, set);
          const totalSkills = set.skills.length;
          const isExpanded = activeOpenId === set.id;

          return (
            <article
              key={set.id}
              className={styles.setTile}
              data-active={isCurrent || undefined}
              data-done={isDone || undefined}
              data-expanded={isExpanded || undefined}
              onMouseEnter={() => setHoveredId(set.id)}
              onMouseLeave={() => setHoveredId((curr) => (curr === set.id ? null : curr))}
              onClick={() => setPinnedId((curr) => (curr === set.id ? null : set.id))}
              aria-expanded={isExpanded}
            >
              <div>
                {/* Шапка плитки */}
                <div className={styles.setTileHead}>
                  <div className={styles.setTileTitleBox}>
                    <span className={styles.setTileNumber}>Сет {set.number}</span>
                    <h4 className={styles.setTileTitle}>{set.title}</h4>
                  </div>

                  {isCurrent && (
                    <span className={styles.tileActiveBadge}>
                      <span className={styles.pulseDot} aria-hidden="true" />
                      Активен
                    </span>
                  )}
                  {!isCurrent && isBest && (
                    <span className={styles.tileBestBadge} title="Ассистент рекомендует этот сет следующим">
                      <Icon name="sparkles" size={11} /> Совет
                    </span>
                  )}
                  {isDone && !isCurrent && (
                    <span className={styles.tileDoneBadge}>
                      <Icon name="check" size={11} /> Пройден
                    </span>
                  )}
                </div>

                {/* Мета-информация плитки */}
                <div className={styles.setTileMeta}>
                  <span>{set.area}</span>
                  <span className={styles.setTileProgressCount}>
                    {closedCount}/{totalSkills} закрыто · до {formatShort(set.deadline)}
                  </span>
                </div>

                {/* Дефолтный компактный вид: мини-пилюли тем */}
                <div className={styles.tilePillList}>
                  {set.skills.map((id) => (
                    <span key={id} className={styles.tilePill} data-state={model.states[id]}>
                      <StateGlyph state={model.states[id]} size={9} />
                      <span>{skillById(id).name}</span>
                    </span>
                  ))}
                </div>

                {/* Раскрывающаяся информация (при наведении / тапе) */}
                <div className={styles.tileDetails}>
                  <div className={styles.tileDetailsInner}>
                    {set.why && (
                      <p className={styles.tileWhy}>
                        <Icon name="sparkles" size={11} /> {set.why}
                      </p>
                    )}

                    <div className={styles.tileTopics}>
                      {set.skills.map((id) => {
                        const skill = skillById(id);
                        const state = model.states[id];
                        const topicSummary = TOPICS[id]?.summary;

                        return (
                          <div
                            key={id}
                            className={styles.tileTopicItem}
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpen(set.id, id);
                            }}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                e.stopPropagation();
                                onOpen(set.id, id);
                              }
                            }}
                            title={`Нажми, чтобы открыть тему «${skill.name}»`}
                          >
                            <div className={styles.tileTopicHead}>
                              <div className={styles.tileTopicNameGroup}>
                                <StateGlyph state={state} size={11} />
                                <span className={styles.tileTopicName}>{skill.name}</span>
                                {skill.root && <span className={styles.rootTag}>корень</span>}
                              </div>
                              <span className={styles.tileTopicState} data-state={state}>
                                {STATE_LABEL[state]}
                              </span>
                            </div>

                            {topicSummary && (
                              <p className={styles.tileTopicSummary}>
                                {topicSummary}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>

              {/* Соединенный стильный блок действий внизу */}
              <div className={styles.tileActionGroup}>
                <div className={styles.tileActionPill}>
                  {isCurrent ? (
                    <>
                      <span className={styles.tileActiveLabel}>
                        <Icon name="check" size={13} /> Активный
                      </span>
                      <button
                        type="button"
                        className={styles.tileOpenBtn}
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpen(set.id);
                        }}
                        title="Открыть материалы сета"
                      >
                        Открыть →
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        className={styles.tileSelectBtn}
                        onClick={(e) => {
                          e.stopPropagation();
                          onTake(set.id);
                        }}
                        aria-label={`Выбрать сет ${set.number} как активный`}
                      >
                        <Icon name="check" size={13} />
                        {isDone ? "Выбрать снова" : "Выбрать сет"}
                      </button>
                      <button
                        type="button"
                        className={styles.tileOpenBtn}
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpen(set.id);
                        }}
                        title="Посмотреть сет"
                      >
                        Обзор
                      </button>
                    </>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
