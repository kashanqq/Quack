"use client";

// "Choice" page (front-end only). Flow per the Figma screens: rotating greeting -> first message
// opens the chat and the "Как я тебя вижу" panel -> the assistant asks for what's missing ->
// summary with confirm / edit buttons -> an edit is sent as a correction and refreshes the profile.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CONFIRM_REPLY,
  EMPTY_PROFILE,
  extract,
  fieldValue,
  placeholderFor,
  planReply,
  readiness,
  type FieldKey,
  type Profile,
} from "./assistant";
import { ChatMessage, type ChatMsg } from "./ChatMessage";
import { CustomScrollbar } from "./CustomScrollbar";
import { ModeSwitch, type Mode } from "./ModeSwitch";
import { ProfilePanel } from "./ProfilePanel";
import { Topbar } from "./Topbar";
import styles from "./choice.module.css";

const GREETINGS = [
  ["Привет!", "Куда целишься после школы?"],
  ["IT, Бизнес, Медицина,", "Еще не определился?"],
];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const prefersReducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function ChoiceApp({ onRestart }: { onRestart: () => void }) {
  const [stage, setStage] = useState<"intro" | "chat">("intro");
  const [mode, setMode] = useState<Mode>("choice");
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [confirmed, setConfirmed] = useState(false);
  const [versions, setVersions] = useState<Partial<Record<FieldKey, number>>>({});
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [placeholder, setPlaceholder] = useState("Люблю бананы и хочу в IT...");
  const [sentTick, setSentTick] = useState(0);
  const [greeting, setGreeting] = useState({ current: 0, leaving: -1 });

  // Mirrors of state that the async assistant flow reads without waiting for a render
  const profileRef = useRef(profile);
  const summarySentRef = useRef(false);
  const busyRef = useRef(false);
  const idRef = useRef(0);
  const mounted = useRef(true);

  const messagesRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    mounted.current = true;
    inputRef.current?.focus();
    return () => {
      mounted.current = false;
    };
  }, []);

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

  const setBusyState = (value: boolean) => {
    busyRef.current = value;
    setBusy(value);
  };

  const updateMsg = useCallback((id: number, patch: Partial<ChatMsg> | ((m: ChatMsg) => Partial<ChatMsg>)) => {
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

  /* ---------- Composer ---------- */

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busyRef.current) return;

    setInput("");
    setSentTick((t) => t + 1);
    setBusyState(true);

    if (stage === "intro") {
      setStage("chat");
      await sleep(prefersReducedMotion() ? 0 : 450);
    }

    addUserMessage(text);
    await respond(text);
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
    setPlaceholder("Спроси что угодно о поступлении...");
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

  return (
    <div className={styles.page}>
      <Topbar onRestart={onRestart} />

      <main className={styles.app} data-stage={stage} data-mode={mode}>
        <aside className={styles.sidebar} aria-label="Программы">
          <h2 className={styles.sidebarTitle}>Программы</h2>
          <ul className={styles.sidebarList} />
          <p className={styles.sidebarEmpty}>Расскажи о себе — и здесь появятся программы под тебя.</p>
        </aside>

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
                  {messages.map((msg) => (
                    <ChatMessage
                      key={msg.id}
                      msg={msg}
                      onConfirm={onConfirm}
                      onEditStart={onEditStart}
                      onEditCancel={onEditCancel}
                      onEditSave={onEditSave}
                    />
                  ))}
                </div>
                <CustomScrollbar target={messagesRef} className={styles.scrollbarChat} />
              </div>
            </div>

            <div className={`${styles.view} ${styles.viewPrep}`} aria-hidden={mode !== "prep"}>
              <h2 className={styles.prepTitle}>Подготовка</h2>
              <p className={styles.prepText}>
                Откроется, когда ты сохранишь первую программу: здесь появятся требования, вехи и первый сет.
              </p>
            </div>
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

          <ModeSwitch mode={mode} onChange={setMode} />
        </section>

        <ProfilePanel profile={profile} readiness={readiness(profile, confirmed)} versions={versions} />
      </main>
    </div>
  );
}
