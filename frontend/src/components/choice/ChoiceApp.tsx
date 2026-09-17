"use client";

// "Choice" page (front-end only). The chat is the main surface; programs arrive in it as cards
// after the summary is confirmed. The left column holds the Выбор / Подготовка switch, the
// programs (picks, favourites, comparison) and chat history. Both side panels can be dragged
// to resize or collapsed; the workspace is kept in localStorage.

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import {
  CONFIRM_REPLY,
  EMPTY_PROFILE,
  editField,
  extract,
  fieldValue,
  placeholderFor,
  planReply,
  readiness,
  type FieldKey,
  type Profile,
} from "./assistant";
import { Dashboard } from "../dashboard/Dashboard";
import { PrepView } from "../prep/PrepView";
import type { PrepTab } from "../prep/prepModel";
import { ChatMessage, type ChatMsg } from "./ChatMessage";
import { CompareView } from "./CompareView";
import { CustomScrollbar } from "./CustomScrollbar";
import { ProfilePanel } from "./ProfilePanel";
import { ProgramCards, ProgramDrawer, type ProgramActions } from "./ProgramUi";
import { recommend } from "./programs";
import { ResizeHandle } from "./ResizeHandle";
import { Sidebar, type ChatSummary, type Mode, type SidebarTab } from "./Sidebar";
import { Topbar } from "./Topbar";
import styles from "./choice.module.css";
import layout from "./layout.module.css";

const GREETINGS = [
  ["Привет!", "Куда целишься после школы?"],
  ["IT, Бизнес, Медицина,", "Еще не определился?"],
];

// Side panel geometry, px
const RAIL_W = 72;
const LEFT_DEFAULT = 302;
const LEFT_MIN = 240;
const LEFT_MAX = 440;
const LEFT_SNAP = 160; // released narrower than this -> collapse to the icon rail
const RIGHT_DEFAULT = 620;
const RIGHT_MIN = 380;
const RIGHT_MAX = 760;
const RIGHT_SNAP = 300; // released narrower than this -> hide
const MAX_COMPARE = 4;
const CHAT_MIN = 460; // below this the profile panel turns into an overlay
const PHONE_MAX = 760;
const LAYOUT_KEY = "quack-choice-layout";
const WORKSPACE_KEY = "quack-choice-workspace";
const INTRO_PLACEHOLDER = "Люблю бананы и хочу в IT...";

type LeftPanel = { width: number; collapsed: boolean; lastWidth: number; userSet: boolean };
type RightPanel = { width: number; hidden: boolean; lastWidth: number };
type ChatItem = ChatMsg & { programs?: string[] };
type Session = ChatSummary & { messages: ChatItem[] };

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const prefersReducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

export function ChoiceApp({ onRestart }: { onRestart: () => void }) {
  const [stage, setStage] = useState<"intro" | "chat">("intro");
  const [mode, setMode] = useState<Mode>("dashboard");
  const [prepTab, setPrepTab] = useState<PrepTab>("overview");
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [confirmed, setConfirmed] = useState(false);
  const [versions, setVersions] = useState<Partial<Record<FieldKey, number>>>({});
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [placeholder, setPlaceholder] = useState(INTRO_PLACEHOLDER);
  const [sentTick, setSentTick] = useState(0);
  const [greeting, setGreeting] = useState({ current: 0, leaving: -1 });

  // Programs
  const [picks, setPicks] = useState<string[]>([]);
  const [saved, setSaved] = useState<string[]>([]);
  const [compare, setCompare] = useState<string[]>([]);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [view, setView] = useState<"chat" | "compare">("chat");
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>("picks");
  const [toast, setToast] = useState<string | null>(null);

  // Chat history
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const activeChatRef = useRef<string | null>(null);

  // Layout
  const [left, setLeft] = useState<LeftPanel>({ width: LEFT_DEFAULT, collapsed: false, lastWidth: LEFT_DEFAULT, userSet: false });
  const [right, setRight] = useState<RightPanel>({ width: RIGHT_DEFAULT, hidden: false, lastWidth: RIGHT_DEFAULT });
  const [resizing, setResizing] = useState(false);
  const [mobileProgramsOpen, setMobileProgramsOpen] = useState(false);
  const [profileOverlayOpen, setProfileOverlayOpen] = useState(false);
  const [viewportWidth, setViewportWidth] = useState(1920);
  const dragStart = useRef(0);
  const dragWidth = useRef(0);

  // Mirrors of state that the async assistant flow reads without waiting for a render
  const profileRef = useRef(profile);
  // Whether the current chat already has a summary; each chat gets its own
  const summarySentRef = useRef(false);
  const busyRef = useRef(false);
  const idRef = useRef(0);
  const mounted = useRef(true);
  // Effects, not refs: writing must wait until the loaded state has actually been applied,
  // otherwise React's double mount in development saves the empty state over the stored one
  const [workspaceLoaded, setWorkspaceLoaded] = useState(false);
  const [layoutLoaded, setLayoutLoaded] = useState(false);

  const messagesRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    mounted.current = true;
    inputRef.current?.focus();
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    const update = () => setViewportWidth(window.innerWidth);
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  /* ---------- Workspace persistence (profile, programs, chats) ---------- */

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(WORKSPACE_KEY) ?? "null");
      if (stored) {
        profileRef.current = stored.profile ?? EMPTY_PROFILE;
        setProfile(profileRef.current);
        setConfirmed(Boolean(stored.confirmed));
        setPicks(stored.picks ?? []);
        setSaved(stored.saved ?? []);
        setCompare(stored.compare ?? []);
        setSessions(stored.sessions ?? []);
        idRef.current = Math.max(0, ...(stored.sessions ?? []).flatMap((c: Session) => c.messages.map((m) => m.id)));
      }
    } catch {}
    setWorkspaceLoaded(true);
  }, []);

  useEffect(() => {
    if (!workspaceLoaded) return;
    try {
      localStorage.setItem(
        WORKSPACE_KEY,
        JSON.stringify({ profile, confirmed, picks, saved, compare, sessions })
      );
    } catch {}
  }, [workspaceLoaded, profile, confirmed, picks, saved, compare, sessions]);

  // Keep the active chat's stored copy in sync with what is on screen
  useEffect(() => {
    const id = activeChatRef.current;
    if (!id) return;
    const settled = messages.filter((m) => !m.typing);
    setSessions((list) =>
      list.map((c) =>
        c.id === id
          ? { ...c, messages: settled, updatedAt: settled.length !== c.messages.length ? Date.now() : c.updatedAt }
          : c
      )
    );
  }, [messages]);

  /* ---------- Layout persistence ---------- */

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(LAYOUT_KEY) ?? "null");
      if (stored?.left) setLeft({ ...stored.left, collapsed: false });
      if (stored?.right) setRight(stored.right);
    } catch {}
    setLayoutLoaded(true);
  }, []);

  useEffect(() => {
    if (!layoutLoaded || resizing) return;
    try {
      localStorage.setItem(LAYOUT_KEY, JSON.stringify({ left, right }));
    } catch {}
  }, [layoutLoaded, left, right, resizing]);

  useEffect(() => {
    if (!profileOverlayOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setProfileOverlayOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [profileOverlayOpen]);

  /* ---------- Greeting rotation ---------- */

  useEffect(() => {
    if (stage !== "intro") return;
    const timer = setInterval(
      () => setGreeting((g) => ({ current: (g.current + 1) % GREETINGS.length, leaving: g.current })),
      3600
    );
    return () => clearInterval(timer);
  }, [stage]);

  /* ---------- Messages ---------- */

  useEffect(() => {
    const el = messagesRef.current;
    el?.scrollTo({ top: el.scrollHeight, behavior: prefersReducedMotion() ? "auto" : "smooth" });
  }, [messages]);

  // Leaving the comparison once fewer than two programs remain in it
  useEffect(() => {
    if (compare.length < 2) setView("chat");
  }, [compare.length]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(timer);
  }, [toast]);

  const setBusyState = (value: boolean) => {
    busyRef.current = value;
    setBusy(value);
  };

  const updateMsg = useCallback((id: number, patch: Partial<ChatItem> | ((m: ChatItem) => Partial<ChatItem>)) => {
    setMessages((list) => list.map((m) => (m.id === id ? { ...m, ...(typeof patch === "function" ? patch(m) : patch) } : m)));
  }, []);

  // Let "leaving" buttons finish their exit animation, then drop them
  const sweepLeaving = () =>
    setTimeout(() => setMessages((list) => list.map((m) => (m.confirm === "leaving" ? { ...m, confirm: "none" } : m))), 350);

  const addUserMessage = (text: string) =>
    setMessages((list) => [...list, { id: ++idRef.current, role: "user", text, confirm: "none", editable: false }]);

  async function assistantSay(text: string, summary = false) {
    const id = ++idRef.current;
    const reduced = prefersReducedMotion();
    setMessages((list) => [...list, { id, role: "assistant", text: "", typing: true, confirm: "none", editable: false }]);

    await sleep(reduced ? 100 : 700 + Math.min(900, text.length * 12));
    if (!mounted.current) return;

    if (reduced) {
      updateMsg(id, { typing: false, text });
    } else {
      // Quick typewriter, ~70 frames regardless of length
      const step = Math.max(1, Math.ceil(text.length / 70));
      for (let i = step; i < text.length + step; i += step) {
        updateMsg(id, { typing: false, text: text.slice(0, i) });
        await sleep(15);
        if (!mounted.current) return;
      }
    }

    if (summary) {
      // Only the latest summary can be confirmed
      setMessages((list) =>
        list.map((m) =>
          m.id === id ? { ...m, confirm: "shown", editable: true } : m.confirm === "shown" && !m.editing ? { ...m, confirm: "leaving" } : m
        )
      );
      sweepLeaving();
    }
  }

  function applyToProfile(text: string) {
    const before = profileRef.current;
    const { profile: next, changed } = extract(before, text);
    profileRef.current = next;
    setProfile(next);

    const updated = changed.filter((key) => fieldValue(before, key));
    if (updated.length) {
      setVersions((v) => Object.fromEntries([...Object.entries(v), ...updated.map((k) => [k, (v[k] ?? 0) + 1])]));
    }
    setPlaceholder(placeholderFor(next));
    return changed;
  }

  async function respond(text: string, fromEdit = false) {
    const changed = applyToProfile(text);
    if (fromEdit) setConfirmed(false);

    const reply = planReply(profileRef.current, changed, { summarySent: summarySentRef.current, fromEdit });
    if (reply.summary) summarySentRef.current = true;
    await assistantSay(reply.text, reply.summary);
  }

  /* ---------- Programs ---------- */

  const openSidebarTab = (tab: SidebarTab) => {
    setSidebarTab(tab);
    setLeft((l) => (l.collapsed ? { ...l, collapsed: false, width: l.lastWidth, userSet: true } : l));
    openMobilePrograms();
  };

  const programActions: ProgramActions = {
    saved,
    compare,
    onToggleSave: (id) => setSaved((list) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id])),
    onToggleCompare: (id) =>
      setCompare((list) => {
        if (list.includes(id)) return list.filter((x) => x !== id);
        if (list.length >= MAX_COMPARE) {
          setToast(`Можно сравнить до ${MAX_COMPARE} программ — убери одну из сравнения`);
          return list;
        }
        return [...list, id];
      }),
    onOpen: (id) => {
      setMobileProgramsOpen(false);
      setDetailId(id);
    },
  };

  const openCompare = () => {
    if (compare.length < 2) return;
    setDetailId(null);
    setMobileProgramsOpen(false);
    setMode("choice");
    setView("compare");
  };

  // Chat shortcuts once programs exist: "сравни…", "избранное…"
  async function handleIntent(text: string) {
    if (!picks.length) return false;
    const t = text.toLowerCase();
    if (/сравн/.test(t)) {
      if (compare.length >= 2) {
        openCompare();
        await assistantSay("Открыл сравнение — вернуться в чат можно стрелкой слева сверху.");
      } else {
        await assistantSay("Отметь «Сравнить» на двух–четырёх карточках, и я поставлю их рядом.");
      }
      return true;
    }
    if (/избранн|сохран/.test(t)) {
      openSidebarTab("saved");
      await assistantSay(saved.length ? "Открыл избранное в панели слева." : "Пока в избранном пусто — нажми ☆ на карточке.");
      return true;
    }
    return false;
  }

  /* ---------- Composer ---------- */

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busyRef.current) return;

    setInput("");
    setSentTick((t) => t + 1);
    setBusyState(true);

    if (!activeChatRef.current) {
      const id = `chat-${Date.now()}`;
      const title = text.length > 42 ? `${text.slice(0, 40)}…` : text;
      activeChatRef.current = id;
      setActiveChatId(id);
      setSessions((list) => [{ id, title, updatedAt: Date.now(), messages: [] }, ...list]);
    }

    if (stage === "intro") {
      setStage("chat");
      // The programs panel shrinks to its icon rail while chatting, unless the user arranged it
      setLeft((l) => (l.userSet ? l : { ...l, collapsed: true }));
      await sleep(prefersReducedMotion() ? 0 : 450);
    }

    addUserMessage(text);
    if (!(await handleIntent(text))) await respond(text);
    if (!mounted.current) return;
    setBusyState(false);
    inputRef.current?.focus();
  }

  /* ---------- Summary: confirm / edit ---------- */

  async function onConfirm(id: number) {
    if (busyRef.current) return;
    updateMsg(id, { confirm: "leaving" });
    sweepLeaving();
    setConfirmed(true);
    setBusyState(true);
    await assistantSay(CONFIRM_REPLY);
    if (!mounted.current) return;

    const ids = recommend(profileRef.current);
    setPicks(ids);
    setSidebarTab("picks");
    setMessages((list) => [
      ...list,
      { id: ++idRef.current, role: "assistant", text: "", confirm: "none", editable: false, programs: ids },
    ]);
    setPlaceholder("Сравни программы или спроси что угодно...");
    setBusyState(false);
  }

  function onEditStart(id: number) {
    if (busyRef.current) return;
    updateMsg(id, (m) => ({ editing: true, confirmBeforeEdit: m.confirm, confirm: "shown" }));
  }

  function onEditCancel(id: number) {
    updateMsg(id, (m) => ({ editing: false, confirm: m.confirmBeforeEdit ?? "none" }));
  }

  async function onEditSave(id: number, original: string, edited: string) {
    // As in the design: the edited summary keeps only the pencil
    updateMsg(id, { editing: false, confirm: "leaving" });
    sweepLeaving();

    const text = edited.trim();
    if (!text || text === original) return;

    const correction = text.replace(/^.*?резюме понимания:\s*/i, "");
    addUserMessage(correction);
    setBusyState(true);
    await respond(correction, true);
    if (!mounted.current) return;
    setBusyState(false);
  }

  /* ---------- Chat history ---------- */

  function showChat(id: string | null, list: ChatItem[]) {
    activeChatRef.current = id;
    setActiveChatId(id);
    summarySentRef.current = list.some((m) => m.role === "assistant" && m.editable);
    setMessages(list);
    setStage(list.length ? "chat" : "intro");
    setGreeting({ current: 0, leaving: -1 });
    setView("chat");
    setDetailId(null);
    setMode("choice");
    setMobileProgramsOpen(false);
    setInput("");
    const p = profileRef.current;
    setPlaceholder(p.direction ? placeholderFor(p) : INTRO_PLACEHOLDER);
    requestAnimationFrame(() => inputRef.current?.focus());
  }

  const selectChat = (id: string) => {
    const chat = sessions.find((c) => c.id === id);
    if (chat && !busyRef.current) showChat(id, chat.messages);
  };

  const deleteChat = (id: string) => {
    if (busyRef.current) return;
    setSessions((list) => list.filter((c) => c.id !== id));
    if (id === activeChatRef.current) showChat(null, []);
  };

  const changeMode = (next: Mode) => {
    setMode(next);
    setView("chat");
    setDetailId(null);
  };

  const restart = () => {
    try {
      localStorage.removeItem(WORKSPACE_KEY);
    } catch {}
    onRestart();
  };

  /* ---------- Student profile ---------- */

  // On phones and cramped windows the profile and the left column open over the chat: never both at once
  const openMobilePrograms = () => {
    setProfileOverlayOpen(false);
    setMobileProgramsOpen(true);
  };

  const toggleProfileOverlay = () =>
    setProfileOverlayOpen((open) => {
      if (!open) setMobileProgramsOpen(false);
      return !open;
    });

  function onEditField(key: FieldKey, value: string) {
    const next = editField(profileRef.current, key, value);
    profileRef.current = next;
    setProfile(next);
    setVersions((v) => ({ ...v, [key]: (v[key] ?? 0) + 1 }));
    setPlaceholder(placeholderFor(next));
  }

  /* ---------- Panel resizing ---------- */

  const phone = viewportWidth <= PHONE_MAX;
  const leftWidth = left.collapsed ? RAIL_W : left.width;
  const rightAvailable = stage === "chat" && mode === "choice";
  // On laptop-sized windows the panel may not fit beside the chat: then it opens over it
  const roomForRight = viewportWidth - leftWidth - CHAT_MIN;
  const rightOverlay = rightAvailable && (phone || roomForRight < RIGHT_MIN);
  const rightWidth = !rightAvailable || right.hidden || rightOverlay ? 0 : Math.min(right.width, roomForRight);
  const profileVisible = rightOverlay ? profileOverlayOpen : rightWidth > 0;

  useEffect(() => {
    if (!rightOverlay) setProfileOverlayOpen(false);
  }, [rightOverlay]);

  const settleLeft = (width: number) =>
    setLeft((l) =>
      width < LEFT_SNAP
        ? { ...l, collapsed: true, width: l.lastWidth, userSet: true }
        : { width: Math.max(width, LEFT_MIN), lastWidth: Math.max(width, LEFT_MIN), collapsed: false, userSet: true }
    );

  const settleRight = (width: number) =>
    setRight((r) => (width < RIGHT_SNAP ? { ...r, hidden: true, width: r.lastWidth } : { width: Math.max(width, RIGHT_MIN), lastWidth: Math.max(width, RIGHT_MIN), hidden: false }));

  const toggleLeft = () =>
    setLeft((l) => (l.collapsed ? { ...l, collapsed: false, width: l.lastWidth, userSet: true } : { ...l, collapsed: true, userSet: true }));

  const toggleRight = () => setRight((r) => ({ ...r, hidden: !r.hidden, width: r.lastWidth }));

  const readinessValue = readiness(profile, confirmed);
  const toggleProfile = rightOverlay ? toggleProfileOverlay : toggleRight;

  const gridStyle = { "--left": `${leftWidth}px`, "--right": `${rightWidth}px` } as CSSProperties;
  const sidebarCollapsed = leftWidth < LEFT_SNAP && !mobileProgramsOpen;

  return (
    <div className={styles.page}>
      <main
        className={`${styles.app} ${resizing ? styles.isResizing : ""}`}
        data-stage={stage}
        data-mode={mode}
        data-view={view}
        style={gridStyle}
      >
        <Topbar
          mode={mode}
          onMode={changeMode}
          onOpenMenu={openMobilePrograms}
          profilePanel={rightAvailable ? { open: profileVisible, readiness: readinessValue, onToggle: toggleProfile } : undefined}
        />

        <aside
          className={`${layout.sidebar} ${mobileProgramsOpen ? layout.sidebarMobileOpen : ""}`}
          aria-label="Навигация"
        >
          <Sidebar
            collapsed={sidebarCollapsed}
            mode={mode}
            tab={sidebarTab}
            picks={picks}
            profile={profile}
            actions={programActions}
            chats={[...sessions].sort((a, b) => b.updatedAt - a.updatedAt)}
            activeChatId={activeChatId}
            onSelectChat={selectChat}
            onDeleteChat={deleteChat}
            onTab={setSidebarTab}
            onToggle={mobileProgramsOpen ? () => setMobileProgramsOpen(false) : toggleLeft}
            onOpenCompare={openCompare}
            onRestart={restart}
            prepTab={prepTab}
            onPrepTab={(tab) => {
              setMode("prep");
              setPrepTab(tab);
              setMobileProgramsOpen(false);
            }}
          />
          <ResizeHandle
            side="left"
            label="Ширина левой панели"
            value={leftWidth}
            min={RAIL_W}
            max={LEFT_MAX}
            onDragStart={() => {
              dragStart.current = dragWidth.current = leftWidth;
              setResizing(true);
              setLeft((l) => ({ ...l, collapsed: false, width: leftWidth }));
            }}
            onDrag={(dx) => {
              dragWidth.current = clamp(dragStart.current + dx, RAIL_W, LEFT_MAX);
              setLeft((l) => ({ ...l, width: dragWidth.current }));
            }}
            onDragEnd={() => {
              setResizing(false);
              settleLeft(dragWidth.current);
            }}
            onNudge={(dx) => settleLeft(clamp(leftWidth + dx, RAIL_W, LEFT_MAX))}
          />
        </aside>
        {mobileProgramsOpen && <div className={layout.mobileBackdrop} onClick={() => setMobileProgramsOpen(false)} />}
        {phone && profileVisible && <div className={styles.profileBackdrop} onClick={() => setProfileOverlayOpen(false)} />}

        <section className={styles.chat}>
          <div className={styles.chatBody}>
            <div className={`${styles.view} ${styles.viewChoice}`}>
              <div className={styles.greeting} aria-live="polite">
                {GREETINGS.map(([first, second], i) => (
                  <p
                    key={first}
                    className={[
                      styles.greetingText,
                      i === greeting.current && styles.isVisible,
                      i === greeting.leaving && styles.isLeaving,
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    aria-hidden={i !== greeting.current}
                  >
                    {first}
                    <br />
                    {second}
                  </p>
                ))}
              </div>

              <div className={styles.messagesWrap}>
                <div className={styles.messages} ref={messagesRef} aria-live="polite">
                  {messages.map((msg) =>
                    msg.programs ? (
                      <div key={msg.id} className={`${styles.msg} ${layout.programsBlock}`} style={{ maxWidth: "none" }}>
                        <ProgramCards ids={msg.programs} profile={profile} actions={programActions} />
                      </div>
                    ) : (
                      <ChatMessage
                        key={msg.id}
                        msg={msg}
                        onConfirm={onConfirm}
                        onEditStart={onEditStart}
                        onEditCancel={onEditCancel}
                        onEditSave={onEditSave}
                      />
                    )
                  )}
                </div>
                <CustomScrollbar target={messagesRef} className={styles.scrollbarChat} />
              </div>

              {view === "compare" && (
                <CompareView
                  ids={compare}
                  profile={profile}
                  onBack={() => setView("chat")}
                  onRemove={programActions.onToggleCompare}
                  onOpen={programActions.onOpen}
                />
              )}

              <ProgramDrawer id={detailId} profile={profile} actions={programActions} onClose={() => setDetailId(null)} />
            </div>

            <div className={`${styles.view} ${styles.viewDashboard}`} aria-hidden={mode !== "dashboard"}>
              {mode === "dashboard" && (
                <Dashboard
                  saved={saved}
                  profile={profile}
                  onUnsave={(id) => setSaved((list) => list.filter((x) => x !== id))}
                  onOpenChoice={() => changeMode("choice")}
                  onOpenPrep={(tab) => {
                    setPrepTab(tab);
                    changeMode("prep");
                  }}
                />
              )}
            </div>

            <div className={`${styles.view} ${styles.viewPrep}`} aria-hidden={mode !== "prep"}>
              {mode === "prep" && (
                <PrepView tab={prepTab} onTab={setPrepTab} saved={saved} onGoToChoice={() => changeMode("choice")} />
              )}
            </div>

            {toast && (
              <div className={layout.toast} role="status">
                {toast}
              </div>
            )}
          </div>

          <form className={styles.composer} autoComplete="off" onSubmit={onSubmit}>
            <input
              ref={inputRef}
              className={styles.composerInput}
              name="message"
              type="text"
              value={input}
              placeholder={placeholder}
              aria-label="Сообщение"
              onChange={(e) => setInput(e.target.value)}
            />
            <button
              key={sentTick}
              className={`${styles.composerSend} ${sentTick ? styles.isSent : ""}`}
              type="submit"
              aria-label="Отправить"
              disabled={!input.trim() || busy}
            >
              <img src="/assets/send-arrow.svg" alt="" />
            </button>
          </form>
        </section>

        <aside
          className={`${styles.profile} ${rightOverlay && profileOverlayOpen ? styles.profileOverlay : ""}`}
          aria-label="Профиль студента"
          aria-hidden={!profileVisible}
        >
          {rightAvailable && !rightOverlay && (
            <ResizeHandle
              side="right"
              label="Ширина профиля студента"
              value={rightWidth}
              min={0}
              max={RIGHT_MAX}
              onDragStart={() => {
                dragStart.current = dragWidth.current = rightWidth;
                setResizing(true);
                setRight((r) => ({ ...r, hidden: false, width: rightWidth }));
              }}
              onDrag={(dx) => {
                dragWidth.current = clamp(dragStart.current - dx, 0, RIGHT_MAX);
                setRight((r) => ({ ...r, width: dragWidth.current }));
              }}
              onDragEnd={() => {
                setResizing(false);
                settleRight(dragWidth.current);
              }}
              onNudge={(dx) => settleRight(clamp(rightWidth - dx, 0, RIGHT_MAX))}
            />
          )}
          <ProfilePanel
            profile={profile}
            readiness={readinessValue}
            versions={versions}
            onEdit={onEditField}
            onHide={() =>
              rightOverlay ? setProfileOverlayOpen(false) : setRight((r) => ({ ...r, hidden: true, width: r.lastWidth }))
            }
          />
        </aside>
      </main>
    </div>
  );
}
