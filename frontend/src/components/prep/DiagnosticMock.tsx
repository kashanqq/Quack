"use client";

import { useState } from "react";
import { Icon } from "../choice/Icon";
import {
  DIAGNOSTIC_8_QUESTIONS,
  evaluateDiagnostic,
  type DiagnosticResultSummary,
} from "./diagnosticData";
import styles from "./prep.module.css";

type Props = {
  onComplete: (summary: DiagnosticResultSummary) => void;
  onClose: () => void;
  onSkip?: () => void;
};

/**
 * Обязательный входной мок-тест на 8 вопросов для новых пользователей.
 * Прототип замера: 8 ключевых вопросов по алгебре, геометрии и анализу данных.
 * Определяет стартовую готовность, ловушки и калибрует персональный маршрут.
 */
export function DiagnosticMock({ onComplete, onClose, onSkip }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [isFinished, setIsFinished] = useState(false);

  const total = DIAGNOSTIC_8_QUESTIONS.length;
  const currentQ = DIAGNOSTIC_8_QUESTIONS[currentIndex];

  const handleSelect = (optionIndex: number) => {
    if (selectedOption !== null) return; // уже ответил на текущий вопрос
    setSelectedOption(optionIndex);
    setAnswers((prev) => ({ ...prev, [currentQ.id]: optionIndex }));
  };

  const handleNext = () => {
    if (currentIndex < total - 1) {
      setCurrentIndex((prev) => prev + 1);
      setSelectedOption(answers[DIAGNOSTIC_8_QUESTIONS[currentIndex + 1].id] ?? null);
    } else {
      setIsFinished(true);
    }
  };

  const handleRestart = () => {
    setCurrentIndex(0);
    setAnswers({});
    setSelectedOption(null);
    setIsFinished(false);
  };

  const summary = evaluateDiagnostic(answers);
  const percent = Math.round((summary.score / total) * 100);

  return (
    <div className={styles.diagnosticModalOverlay} role="dialog" aria-modal="true" aria-labelledby="diag-title">
      <div className={styles.diagnosticModalBox}>
        {/* Шапка модального окна */}
        <header className={styles.diagnosticModalHead}>
          <div>
            <div className={styles.diagnosticBadgeGroup}>
              <span className={styles.diagnosticTag}>
                <Icon name="sparkles" size={12} /> Входной замер
              </span>
              <span className={styles.diagnosticSubtitle}>8 вопросов · калибровка маршрута</span>
            </div>
            <h3 id="diag-title" className={styles.diagnosticTitle}>
              {isFinished ? "Итог входного замера" : `Вопрос ${currentIndex + 1} из ${total}`}
            </h3>
          </div>

          <div className={styles.diagHeadActions}>
            {onSkip && (
              <button
                type="button"
                className={styles.diagSkipBtn}
                onClick={onSkip}
                title="Скинуть тест и использовать базовые оценки"
              >
                Скинуть тест
              </button>
            )}
            <button
              type="button"
              className={styles.topicClose}
              onClick={onClose}
              aria-label="Закрыть тест"
              title="Закрыть замер"
            >
              <Icon name="x" size={16} />
            </button>
          </div>
        </header>

        {/* Индикатор прогресса (8 точек) */}
        {!isFinished && (
          <div className={styles.diagnosticDots} aria-label="Прогресс по вопросам">
            {DIAGNOSTIC_8_QUESTIONS.map((q, idx) => {
              const answeredIndex = answers[q.id];
              const isCurrent = idx === currentIndex;
              let dotState = "empty";
              if (answeredIndex !== undefined) {
                dotState = q.options[answeredIndex]?.correct ? "correct" : "wrong";
              } else if (isCurrent) {
                dotState = "current";
              }
              return (
                <span
                  key={q.id}
                  className={styles.diagnosticDot}
                  data-state={dotState}
                  title={`Вопрос ${idx + 1}: ${q.skillName}`}
                />
              );
            })}
          </div>
        )}

        {/* Экран прохождения вопросов */}
        {!isFinished ? (
          <div className={styles.diagnosticBody}>
            {/* Карточка текущего вопроса */}
            <div className={styles.diagnosticQuestionCard}>
              <div className={styles.diagnosticAreaMeta}>
                <span>{currentQ.area}</span>
                <span>·</span>
                <span className={styles.diagnosticSkillName}>{currentQ.skillName}</span>
              </div>

              <p className={styles.diagnosticQuestionText}>{currentQ.question}</p>

              {/* 4 варианта ответа */}
              <div className={styles.diagnosticOptionsGrid}>
                {currentQ.options.map((opt, oIdx) => {
                  const isPicked = selectedOption === oIdx;
                  let stateClass = "";
                  if (selectedOption !== null) {
                    if (opt.correct) stateClass = styles.optCorrect;
                    else if (isPicked) stateClass = styles.optWrong;
                  }

                  return (
                    <button
                      key={oIdx}
                      type="button"
                      disabled={selectedOption !== null}
                      className={`${styles.diagnosticOptionBtn} ${stateClass} ${isPicked ? styles.optSelected : ""}`}
                      onClick={() => handleSelect(oIdx)}
                    >
                      <span className={styles.diagnosticOptionIndex}>
                        {String.fromCharCode(65 + oIdx)}
                      </span>
                      <span className={styles.diagnosticOptionLabel}>{opt.label}</span>
                      {selectedOption !== null && opt.correct && (
                        <Icon name="check" size={15} className={styles.optCheckIcon} />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Пояснение и предупреждение о ловушке после ответа */}
              {selectedOption !== null && (
                <div className={styles.diagnosticFeedback}>
                  {currentQ.options[selectedOption]?.trap && (
                    <div className={styles.diagnosticTrapAlert}>
                      <Icon name="triangle-alert" size={14} />
                      <span>Ловушка: {currentQ.options[selectedOption].trap}</span>
                    </div>
                  )}

                  <div className={styles.diagnosticExplainBox}>
                    <strong>Разбор:</strong> {currentQ.explanation}
                  </div>
                </div>
              )}
            </div>

            {/* Футер вопроса: кнопка дальше */}
            <footer className={styles.diagnosticFoot}>
              {onSkip && (
                <button
                  type="button"
                  className={styles.diagSkipLink}
                  onClick={onSkip}
                  title="Скинуть тест и применить базовые оценки"
                >
                  Скинуть тест (взять базовые оценки)
                </button>
              )}
              <button
                type="button"
                disabled={selectedOption === null}
                className={styles.primary}
                onClick={handleNext}
              >
                {currentIndex < total - 1 ? (
                  <>
                    Следующий вопрос <Icon name="chevron-right" size={16} />
                  </>
                ) : (
                  <>
                    Завершить замер <Icon name="check" size={16} />
                  </>
                )}
              </button>
            </footer>
          </div>
        ) : (
          /* Экран результатов */
          <div className={styles.diagnosticResultBody}>
            <div className={styles.diagnosticScoreCard}>
              <div className={styles.diagnosticScoreNum}>
                <strong>{summary.score}</strong> / {total}
              </div>
              <p className={styles.diagnosticPercent}>{percent}% верных ответов</p>

              <p className={styles.diagnosticVerdict}>
                {percent >= 75
                  ? "Отличная база! Сильные стороны зафиксированы. Ассистент ускорит стартовые сеты и сфокусируется на продвинутых темах."
                  : percent >= 50
                  ? "Хороший старт! Выявлены ключевые темы и ловушки — ассистент скорректировал маршрут для закрытия слабых мест."
                  : "Диагностика выявила базовые пробелы. Стартовые сеты перестроены от фундамента, чтобы не допустить ошибок выше."}
              </p>
            </div>

            {/* Сводка по темам */}
            <div className={styles.diagnosticBreakdown}>
              {summary.solidSkills.length > 0 && (
                <div className={styles.breakdownSection}>
                  <p className={styles.breakdownTitleOk}>
                    <Icon name="check" size={14} /> Твёрдо усвоенные темы ({summary.solidSkills.length})
                  </p>
                  <ul className={styles.breakdownList}>
                    {summary.solidSkills.map((s, idx) => (
                      <li key={idx} className={styles.breakdownChipOk}>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {summary.attentionSkills.length > 0 && (
                <div className={styles.breakdownSection}>
                  <p className={styles.breakdownTitleWarn}>
                    <Icon name="triangle-alert" size={14} /> Требуют укрепления в маршруте ({summary.attentionSkills.length})
                  </p>
                  <ul className={styles.breakdownList}>
                    {summary.attentionSkills.map((s, idx) => (
                      <li key={idx} className={styles.breakdownChipWarn}>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {summary.trapsCaught.length > 0 && (
                <div className={styles.breakdownSection}>
                  <p className={styles.breakdownTitleTrap}>
                    Зафиксированные ловушки ({summary.trapsCaught.length})
                  </p>
                  <ul className={styles.trapsList}>
                    {summary.trapsCaught.map((t, idx) => (
                      <li key={idx}>{t}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Футер результатов */}
            <footer className={styles.diagnosticResultFoot}>
              <button
                type="button"
                className={styles.primary}
                onClick={() => onComplete(summary)}
              >
                Применить и открыть маршрут <Icon name="chevron-right" size={16} />
              </button>
              <button
                type="button"
                className={styles.secondary}
                onClick={handleRestart}
              >
                Пройти заново
              </button>
            </footer>
          </div>
        )}
      </div>
    </div>
  );
}
