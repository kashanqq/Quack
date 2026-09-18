"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { PixelDuck } from "@/components/duck/PixelDuck";
import { auth } from "./auth";
import type { User } from "./contract";
import { store } from "./store";
import styles from "./account.module.css";

type Account = { user: User; signOut: () => Promise<void> };

const AccountContext = createContext<Account | null>(null);

/** The signed-in student; only inside AuthGate */
export function useAccount() {
  const account = useContext(AccountContext);
  if (!account) throw new Error("useAccount outside AuthGate");
  return account;
}

/**
 * App pages open only for a signed-in student, and only once that student's state is loaded —
 * so every screen below can read it synchronously, the same way whether it came from this browser
 * or from the server. Without a session the student goes to /login and comes back afterwards.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const me = await auth.me();
      if (!alive) return;
      if (!me) {
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        return;
      }
      await store.open(me);
      if (alive) setUser(me);
    })();
    return () => {
      alive = false;
    };
  }, [pathname, router]);

  if (!user) {
    return (
      <div className={styles.gate} role="status" aria-live="polite">
        <PixelDuck tempo="fast" className={styles.gateDuck} />
        <span className={styles.srOnly}>Загружаем твои данные</span>
      </div>
    );
  }

  const signOut = async () => {
    store.close();
    await auth.logout();
    // A full load, so nothing of this student stays in memory for the next one
    window.location.assign("/");
  };

  return <AccountContext.Provider value={{ user, signOut }}>{children}</AccountContext.Provider>;
}
