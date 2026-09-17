"use client";

import { TransitionLink } from "@/components/transition/TransitionLink";
import { Icon } from "./Icon";
import { ProfileToggle } from "./ProfilePanel";
import styles from "./choice.module.css";
import layout from "./layout.module.css";

type TopbarProps = {
  /** Opens the left column (programs, chats, account) */
  onOpenMenu: () => void;
  /** Toggle for the student profile; omitted while it isn't available */
  profilePanel?: { open: boolean; readiness: number; onToggle: () => void };
};

/** Phones only: on larger screens the logo and account live in the left column. */
export function Topbar({ onOpenMenu, profilePanel }: TopbarProps) {
  return (
    <header className={styles.topbar}>
      <button type="button" className={layout.iconButton} aria-label="Меню: программы и чаты" onClick={onOpenMenu}>
        <Icon name="menu" />
      </button>
      <TransitionLink className={styles.topbarLogo} href="/">
        Quack<span className={styles.accent}>!</span>
      </TransitionLink>
      {profilePanel && (
        <ProfileToggle
          className={styles.topbarProfile}
          open={profilePanel.open}
          readiness={profilePanel.readiness}
          onClick={profilePanel.onToggle}
        />
      )}
    </header>
  );
}
