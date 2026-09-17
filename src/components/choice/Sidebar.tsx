"use client";

import { useRef } from "react";
import type { Profile } from "./assistant";
import { Icon, type IconName } from "./Icon";
import { LevelDot, type ProgramActions } from "./ProgramUi";
import { evaluate, programById } from "./programs";
import styles from "./layout.module.css";

export type Mode = "choice" | "prep";
export type SidebarTab = "picks" | "saved" | "compare";

export type ChatSummary = { id: string; title: string; updatedAt: number };

const MODES: { mode: Mode; label: string; icon: IconName }[] = [
  { mode: "choice", label: "Выбор", icon: "graduation-cap" },
  { mode: "prep", label: "Подготовка", icon: "book-open-check" },
];

const TABS: { tab: SidebarTab; label: string; icon: IconName }[] = [
  { tab: "picks", label: "Подборка", icon: "sparkles" },
  { tab: "saved", label: "Избранное", icon: "star" },
  { tab: "compare", label: "Сравнение", icon: "git-compare" },
];

type SidebarProps = {
  collapsed: boolean;
  mode: Mode;
  onMode: (mode: Mode) => void;
  tab: SidebarTab;
  onTab: (tab: SidebarTab) => void;
  picks: string[];
  profile: Profile;
  actions: ProgramActions;
  chats: ChatSummary[];
  activeChatId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
  onToggle: () => void;
  onOpenCompare: () => void;
};

const timeLabel = (ts: number) => {
  const d = new Date(ts);
  const today = new Date();
  return d.toDateString() === today.toDateString()
    ? d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
};

/**
 * Left column: section switch (Выбор / Подготовка) at the top, like Claude's Chat / Code,
 * then programs (picks, favourites, comparison) and chat history. Collapses to an icon rail.
 */
export function Sidebar(props: SidebarProps) {
  const { collapsed, mode, onMode, tab, onTab, picks, profile, actions, chats, activeChatId } = props;
  const historyRef = useRef<HTMLElement>(null);

  const counts: Record<SidebarTab, number> = {
    picks: picks.length,
    saved: actions.saved.length,
    compare: actions.compare.length,
  };

  const modeSwitch = (
    <div className={`${styles.modeSwitch} ${collapsed ? styles.modeSwitchRail : ""}`} role="tablist" aria-label="Раздел">
      {MODES.map((m) => (
        <button
          key={m.mode}
          type="button"
          role="tab"
          aria-selected={mode === m.mode}
          className={styles.modeButton}
          title={m.label}
          onClick={() => onMode(m.mode)}
        >
          <Icon name={m.icon} size={18} />
          {!collapsed && <span>{m.label}</span>}
        </button>
      ))}
    </div>
  );

  if (collapsed) {
    return (
      <div className={styles.rail}>
        <button type="button" className={styles.iconButton} aria-label="Развернуть левую панель" onClick={props.onToggle}>
          <Icon name="panel-left-open" />
        </button>
        {modeSwitch}
        {mode === "choice" && (
          <>
            <span className={styles.railDivider} />
            <button type="button" className={styles.iconButton} aria-label="Новый чат" title="Новый чат" onClick={props.onNewChat}>
              <Icon name="plus" />
            </button>
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
      </div>
    );
  }

  const ids = tab === "picks" ? picks : tab === "saved" ? actions.saved : actions.compare;

  return (
    <div className={styles.sidebarInner}>
      <div className={styles.sidebarHead}>
        {modeSwitch}
        <button type="button" className={styles.iconButton} aria-label="Свернуть левую панель" onClick={props.onToggle}>
          <Icon name="panel-left-close" />
        </button>
      </div>

      {mode === "prep" ? (
        <div className={styles.sidebarScroll} key="prep">
          <p className={styles.sectionLabel}>Подготовка</p>
          <ul className={styles.list}>
            {["Обзор", "Сеты", "Текущий сет"].map((item) => (
              <li key={item} className={`${styles.row} ${styles.rowDisabled}`}>
                <span className={styles.rowMain}>
                  <span className={styles.rowTitle}>{item}</span>
                </span>
                <span className={styles.soon}>скоро</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className={styles.sidebarScroll} key="choice">
          <button type="button" className={styles.newChat} onClick={props.onNewChat}>
            <Icon name="plus" size={18} />
            Новый чат
          </button>

          <section className={styles.section} aria-label="Программы">
            <p className={styles.sectionLabel}>Программы</p>
            <div className={styles.tabs} role="tablist">
              {TABS.map(({ tab: t, label }) => (
                <button key={t} type="button" role="tab" aria-selected={tab === t} className={styles.tab} onClick={() => onTab(t)}>
                  {label}
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
                            <span className={styles.rowTitle}>{program.university}</span>
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
    </div>
  );
}
