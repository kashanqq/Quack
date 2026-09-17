"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import styles from "./choice.module.css";

export type ChatMsg = {
  id: number;
  role: "user" | "assistant";
  text: string;
  typing?: boolean;
  /** Confirm (✓) button state; "leaving" plays the exit animation */
  confirm: "none" | "shown" | "leaving";
  /** Whether the edit (✏) button is available — only on summaries */
  editable: boolean;
  editing?: boolean;
  confirmBeforeEdit?: ChatMsg["confirm"];
};

type ChatMessageProps = {
  msg: ChatMsg;
  onConfirm: (id: number) => void;
  onEditStart: (id: number) => void;
  onEditCancel: (id: number) => void;
  onEditSave: (id: number, original: string, edited: string) => void;
};

export function ChatMessage({ msg, onConfirm, onEditStart, onEditCancel, onEditSave }: ChatMessageProps) {
  const editRef = useRef<HTMLTextAreaElement>(null);
  const [draft, setDraft] = useState(msg.text);

  // Entering edit mode: start from the current text with the caret at the end
  useEffect(() => {
    if (!msg.editing) return;
    setDraft(msg.text);
    requestAnimationFrame(() => {
      const el = editRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(el.value.length, el.value.length);
    });
  }, [msg.editing, msg.text]);

  // Grow with the text so the bubble expands instead of scrolling
  useLayoutEffect(() => {
    const el = editRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [draft, msg.editing]);

  const save = () => onEditSave(msg.id, msg.text, draft);
  const classes = [styles.msg, msg.role === "user" && styles.msgUser, msg.editing && styles.isEditing];

  return (
    <div className={classes.filter(Boolean).join(" ")}>
      <div className={styles.msgBubble}>
        {msg.typing ? (
          <div className={styles.typing} aria-label="Ассистент печатает">
            <span />
            <span />
            <span />
          </div>
        ) : msg.editing ? (
          <textarea
            ref={editRef}
            className={styles.editInput}
            value={draft}
            rows={1}
            aria-label="Правка резюме"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                save();
              } else if (e.key === "Escape") {
                onEditCancel(msg.id);
              }
            }}
          />
        ) : (
          <div className={styles.msgText}>{msg.text}</div>
        )}
      </div>

      {(msg.confirm !== "none" || msg.editable) && (
        <div className={styles.msgActions}>
          {msg.confirm !== "none" && (
            <button
              type="button"
              className={`${styles.iconBtn} ${styles.iconBtnConfirm} ${msg.confirm === "leaving" ? styles.isLeaving : ""}`}
              aria-label={msg.editing ? "Сохранить правку" : "Всё верно"}
              onClick={() => (msg.editing ? save() : onConfirm(msg.id))}
            >
              <span className={`${styles.icon} ${styles.iconCheck}`} />
            </button>
          )}
          {msg.editable && (
            <button
              type="button"
              className={`${styles.iconBtn} ${styles.iconBtnEdit}`}
              aria-label={msg.editing ? "Отменить правку" : "Исправить"}
              onClick={() => (msg.editing ? onEditCancel(msg.id) : onEditStart(msg.id))}
            >
              <span className={`${styles.icon} ${styles.iconPencil}`} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
