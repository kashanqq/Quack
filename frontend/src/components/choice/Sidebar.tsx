"use client";

import { useRef } from "react";
import type { Profile } from "./assistant";
import { Icon, type IconName } from "./Icon";
import { LevelDot, type ProgramActions } from "./ProgramUi";
import { evaluate, programById } from "./programs";
import { DASH_TABS, type DashTab } from "../dashboard/dashboardRules";
import { PREP_SUBS, PREP_TABS, subFor, type PrepSub, type PrepTab } from "../prep/prepModel";
import { UserMenu } from "./UserMenu";
import styles from "./layout.module.css";

export type Mode = "dashboard" | "choice" | "prep";
export type SidebarTab = "picks" | "saved" | "compare";

export type ChatSummary = { id: string; title: string; updatedAt: number };

const TABS: { tab: SidebarTab; label: string; icon: IconName }[] = [
  { tab: "picks", label: "Подборка", icon: "sparkles" },
  { tab: "saved", label: "Избранное", icon: "star" },
  { tab: "compare", label: "Сравнение", icon: "git-compare" },
];

type SidebarProps = {
  collapsed: boolean;
  mode: Mode;
  tab: SidebarTab;
  onTab: (tab: SidebarTab) => void;
  picks: string[];
  profile: Profile;
  actions: ProgramActions;
  chats: ChatSummary[];
  activeChatId: string | null;
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
  onToggle: () => void;
  onOpenCompare: () => void;
  onRestart: () => void;
  prepTab: PrepTab;
  onPrepTab: (tab: PrepTab, sub?: PrepSub) => void;
  prepSub: PrepSub;
  dashTab: DashTab;
  onDashTab: (tab: DashTab) => void;
};

const timeLabel = (ts: number) => {
  const d = new Date(ts);
  const today = new Date();
  return d.toDateString() === today.toDateString()
    ? d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
};

/**
 * Left column: programs (picks, favourites, comparison), chat history and the account at the bottom.
 * Collapses to an icon rail.
 */
export function Sidebar(props: SidebarProps) {
  const { collapsed, mode, tab, onTab, picks, profile, actions, chats, activeChatId } = props;
  const historyRef = useRef<HTMLElement>(null);

  const counts: Record<SidebarTab, number> = {
    picks: picks.length,
    saved: actions.saved.length,
    compare: actions.compare.length,
  };

  if (collapsed) {
    return (
      <div className={styles.rail}>
        <button type="button" className={styles.iconButton} aria-label="Развернуть левую панель" onClick={props.onToggle}>
          <Icon name="panel-left-open" />
        </button>
        <span className={styles.railDivider} />
        {mode === "prep" && (
          <>
            <span className={styles.railDivider} />
            {PREP_TABS.map((t) => (
              <button
                key={t.tab}
                type="button"
                className={styles.iconButton}
                aria-label={t.label}
                title={t.label}
                aria-pressed={props.prepTab === t.tab}
                onClick={() => props.onPrepTab(t.tab)}
              >
                <Icon name={t.icon} />
              </button>
            ))}
            <span className={styles.railDivider} />
            {PREP_SUBS[props.prepTab].map((s) => (
              <button
                key={s.sub}
                type="button"
                className={`${styles.iconButton} ${styles.railSub}`}
                aria-label={`${s.label} — ${s.hint}`}
                title={s.label}
                aria-pressed={subFor(props.prepTab, props.prepSub) === s.sub}
                onClick={() => props.onPrepTab(props.prepTab, s.sub)}
              >
                <Icon name={s.icon} size={16} />
              </button>
            ))}
          </>
        )}
        {mode === "dashboard" && (
          <>
            <span className={styles.railDivider} />
            {DASH_TABS.map((t) => (
              <button
                key={t.tab}
                type="button"
                className={styles.iconButton}
                aria-label={t.label}
                title={t.label}
                aria-pressed={props.dashTab === t.tab}
                onClick={() => props.onDashTab(t.tab)}
              >
                <Icon name={t.icon} />
              </button>
            ))}
          </>
        )}
        {mode !== "prep" && (
          <>
            <span className={styles.railDivider} />
            {TABS.map(({ tab: t, label, icon }) => (
              <button
                key={t}
                type="button"
                className={`${styles.iconButton} ${styles.railButton}`}
                aria-label={label}
                title={label}
                onClick={() => {
                  onTab(t);
                  props.onToggle();
                }}
              >
                <Icon name={icon} />
                {t !== "picks" && counts[t] > 0 && (
                  <span key={counts[t]} className={styles.badge}>
                    {counts[t]}
                  </span>
                )}
              </button>
            ))}
            <button
              type="button"
              className={styles.iconButton}
              aria-label="История чатов"
              title="История чатов"
              onClick={() => {
                props.onToggle();
                // Wait for the panel to expand before scrolling to the history
                setTimeout(() => historyRef.current?.scrollIntoView({ behavior: "smooth" }), 350);
              }}
            >
              <Icon name="history" />
            </button>
          </>
        )}
        <div className={styles.railFoot}>
          <UserMenu onRestart={props.onRestart} compact />
        </div>
      </div>
    );
  }

  const ids = tab === "picks" ? picks : tab === "saved" ? actions.saved : actions.compare;

  return (
    <div className={styles.sidebarInner}>
      <div className={styles.sidebarHead}>
        <p className={styles.sidebarSection}>{mode === "prep" ? "Подготовка" : mode === "dashboard" ? "Дашборд" : "Выбор"}</p>
        <button type="button" className={styles.iconButton} aria-label="Свернуть левую панель" onClick={props.onToggle}>
          <Icon name="panel-left-close" />
        </button>
      </div>

      {mode === "dashboard" ? (
        <div className={styles.sidebarScroll} key="dashboard">
          <ul className={styles.list}>
            {DASH_TABS.map((t, i) => (
              <li
                key={t.tab}
                className={`${styles.row} ${props.dashTab === t.tab ? styles.rowActive : ""}`}
                style={{ animationDelay: `${i * 24}ms` }}
              >
                <button
                  type="button"
                  className={styles.rowMain}
                  aria-current={props.dashTab === t.tab}
                  onClick={() => props.onDashTab(t.tab)}
                >
                  <Icon name={t.icon} size={16} className={styles.rowIcon} />
                  <span className={styles.rowText}>
                    <span className={styles.rowTitle}>{t.label}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>

          <section className={styles.section} aria-label="Сохранённые">
            <p className={styles.sectionLabel}>Сохранённые</p>
            {actions.saved.length === 0 ? (
              <p className={styles.empty}>Нажми ☆ на карточке программы в «Выборе».</p>
            ) : (
              <ul className={styles.list}>
                {actions.saved.map((id, i) => {
                  const program = programById(id);
                  return (
                    <li key={id} className={styles.row} style={{ animationDelay: `${i * 24}ms` }}>
                      <button type="button" className={styles.rowMain} onClick={() => actions.onOpen(id)}>
                        <LevelDot level={evaluate(program, profile).level} />
                        <span className={styles.rowText}>
                          <span className={`${styles.rowTitle} ${styles.rowTitleFull}`}>{program.university}</span>
                          <span className={styles.rowSub}>
                            {program.city} · {program.program}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>
      ) : mode === "prep" ? (
        <div className={styles.sidebarScroll} key="prep">
          <ul className={styles.list}>
            {PREP_TABS.map((t, i) => {
              const open = props.prepTab === t.tab;
              return (
                <li key={t.tab} style={{ animationDelay: `${i * 30}ms` }} className={styles.group}>
                  <div className={`${styles.row} ${open ? styles.rowActive : ""}`}>
                    <button type="button" className={styles.rowMain} aria-current={open} onClick={() => props.onPrepTab(t.tab)}>
                      <Icon name={t.icon} size={16} className={styles.rowIcon} />
                      <span className={styles.rowText}>
                        <span className={styles.rowTitle}>{t.label}</span>
                      </span>
                    </button>
                  </div>
                  {/* Only the open tab unfolds, so the column stays a single list of what is on screen */}
                  {open && (
                    <ul className={styles.subList}>
                      {PREP_SUBS[t.tab].map((s, j) => {
                        const active = subFor(props.prepTab, props.prepSub) === s.sub;
                        return (
                          <li
                            key={s.sub}
                            className={`${styles.row} ${styles.subRow} ${active ? styles.rowActive : ""}`}
                            style={{ animationDelay: `${j * 24}ms` }}
                          >
                            <button
                              type="button"
                              className={styles.rowMain}
                              aria-current={active}
                              onClick={() => props.onPrepTab(t.tab, s.sub)}
                            >
                              <Icon name={s.icon} size={15} className={styles.rowIcon} />
                              <span className={styles.rowText}>
                                <span className={styles.rowTitle}>{s.label}</span>
                                <span className={styles.rowSub}>{s.hint}</span>
                              </span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ) : (
        <div className={styles.sidebarScroll} key="choice">
          <section className={styles.section} aria-label="Программы">
            <p className={styles.sectionLabel}>Программы</p>
            <div className={styles.tabs} role="tablist">
              {TABS.map(({ tab: t, label }) => (
                <button key={t} type="button" role="tab" aria-selected={tab === t} className={styles.tab} onClick={() => onTab(t)}>
                  <span className={styles.tabLabel}>{label}</span>
                  {counts[t] > 0 && <span className={styles.count}>{counts[t]}</span>}
                </button>
              ))}
            </div>

            <div className={styles.tabBody} key={tab}>
              {ids.length === 0 ? (
                <p className={styles.empty}>
                  {tab === "picks" && "Расскажи о себе в чате и подтверди резюме — здесь появится подборка."}
                  {tab === "saved" && "Нажми ☆ на карточке программы, чтобы сохранить её сюда."}
                  {tab === "compare" && "Нажми «Сравнить» на 2–4 программах, чтобы поставить их рядом."}
                </p>
              ) : (
                <ul className={styles.list}>
                  {ids.map((id, i) => {
                    const program = programById(id);
                    const saved = actions.saved.includes(id);
                    return (
                      <li key={id} className={styles.row} style={{ animationDelay: `${i * 40}ms` }}>
                        <button type="button" className={styles.rowMain} onClick={() => actions.onOpen(id)}>
                          <LevelDot level={evaluate(program, profile).level} />
                          <span className={styles.rowText}>
                            <span className={`${styles.rowTitle} ${styles.rowTitleFull}`}>{program.university}</span>
                            <span className={styles.rowSub}>
                              {program.city} · {program.program}
                            </span>
                          </span>
                        </button>
                        {tab === "compare" ? (
                          <button
                            type="button"
                            className={styles.iconButton}
                            aria-label="Убрать из сравнения"
                            onClick={() => actions.onToggleCompare(id)}
                          >
                            <Icon name="x" size={16} />
                          </button>
                        ) : (
                          <button
                            type="button"
                            className={styles.iconButton}
                            aria-pressed={saved}
                            aria-label={saved ? "Убрать из избранного" : "В избранное"}
                            onClick={() => actions.onToggleSave(id)}
                          >
                            <Icon name="star" size={18} />
                          </button>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}

              {tab === "compare" && (
                <>
                  <button type="button" className={styles.sidebarAction} disabled={counts.compare < 2} onClick={props.onOpenCompare}>
                    Открыть сравнение
                  </button>
                  <p className={styles.hint}>Можно сравнить до 4 программ</p>
                </>
              )}
            </div>
          </section>

          <section className={styles.section} aria-label="История чатов" ref={historyRef}>
            <p className={styles.sectionLabel}>Чаты</p>
            {chats.length === 0 ? (
              <p className={styles.empty}>Здесь будут твои разговоры с Quack.</p>
            ) : (
              <ul className={styles.list}>
                {chats.map((chat, i) => (
                  <li
                    key={chat.id}
                    className={`${styles.row} ${chat.id === activeChatId ? styles.rowActive : ""}`}
                    style={{ animationDelay: `${i * 30}ms` }}
                  >
                    <button
                      type="button"
                      className={styles.rowMain}
                      aria-current={chat.id === activeChatId}
                      onClick={() => props.onSelectChat(chat.id)}
                    >
                      <Icon name="message-square" size={16} className={styles.rowIcon} />
                      <span className={styles.rowText}>
                        <span className={styles.rowTitle}>{chat.title}</span>
                        <span className={styles.rowSub}>{timeLabel(chat.updatedAt)}</span>
                      </span>
                    </button>
                    <button
                      type="button"
                      className={`${styles.iconButton} ${styles.rowDelete}`}
                      aria-label={`Удалить чат «${chat.title}»`}
                      onClick={() => props.onDeleteChat(chat.id)}
                    >
                      <Icon name="trash-2" size={16} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
      <div className={styles.sidebarFoot}>
        <UserMenu onRestart={props.onRestart} />
      </div>
    </div>
  );
}
