"use client";

import { useEffect, useState } from "react";
import { copy, DIALOGUES, type ChatTurn } from "./copy";
import { PixelDuck } from "@/components/duck/PixelDuck";
import styles from "./quack.module.css";
import { useRotator } from "./useRotator";

/** Stand-in for the student. `/assets/avatar.svg` is a plain grey disc that
    disappears against the light panel, so the landing draws its own. */
function YouAvatar() {
  return (
    <svg viewBox="0 0 24 24" className={styles.avatarGlyph} aria-hidden="true">
      <circle cx="12" cy="9" r="4" fill="currentColor" />
      <path d="M4 22c0-4.4 3.6-7 8-7s8 2.6 8 7z" fill="currentColor" />
    </svg>
  );
}

/** How long one dialogue stays before the next one starts. */
const DIALOGUE_MS = 10000;
/** The assistant "types" for this long before each of its lines. */
const TYPING_MS = 900;
/** Pause after a line lands, before the next one starts. */
const BEAT_MS = 800;

type ChatThreadProps = { turns: ChatTurn[] };

/** Plays one dialogue: lines land one at a time, the assistant types first. */
function ChatThread({ turns }: ChatThreadProps) {
  const [shown, setShown] = useState(0);
  const [typing, setTyping] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(turns.length);
      return;
    }

    const timers: ReturnType<typeof setTimeout>[] = [];
    let i = 0;

    const step = () => {
      if (i >= turns.length) {
        setTyping(false);
        return;
      }
      const land = () => {
        setTyping(false);
        setShown(++i);
        timers.push(setTimeout(step, BEAT_MS));
      };

      if (turns[i].from === "bot") {
        setTyping(true);
        timers.push(setTimeout(land, TYPING_MS));
      } else {
        land();
      }
    };

    timers.push(setTimeout(step, 400));
    return () => timers.forEach(clearTimeout);
  }, [turns]);

  return (
    <div className={styles.thread}>
      {turns.slice(0, shown).map((turn, i) => (
        <div key={i} className={styles.turn} data-from={turn.from}>
          <span className={styles.avatar} aria-hidden="true">
            {turn.from === "bot" ? <PixelDuck tempo="steady" className={styles.avatarDuck} /> : <YouAvatar />}
          </span>
          <p className={styles.bubble}>{turn.text}</p>
        </div>
      ))}

      {typing && (
        <div className={styles.turn} data-from="bot">
          <span className={styles.avatar} aria-hidden="true">
            <PixelDuck tempo="steady" className={styles.avatarDuck} />
          </span>
          <p className={`${styles.bubble} ${styles.typing}`} aria-label={copy.quack.chat.typing}>
            <i />
            <i />
            <i />
          </p>
        </div>
      )}
    </div>
  );
}

type ChatDemoProps = {
  /** True while this is the open tab — dialogues only rotate when visible. */
  active: boolean;
};

/** Rotates through sample conversations, one every ten seconds. */
export function ChatDemo({ active }: ChatDemoProps) {
  const [index] = useRotator(DIALOGUES.length, DIALOGUE_MS, !active);

  return (
    <div className={styles.chat}>
      <div className={styles.uniHead}>
        <span className={styles.uniCaption}>{copy.quack.chat.caption}</span>
        <span className={styles.demoBadge}>{copy.quack.uni.demo}</span>
      </div>

      {/* Keyed so each dialogue replays its reveal from the top. */}
      <ChatThread key={index} turns={DIALOGUES[index]} />
    </div>
  );
}
