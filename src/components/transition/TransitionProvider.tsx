"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Duck } from "@/components/duck/Duck";
import duckStyles from "@/components/duck/duck.module.css";
import styles from "./transition.module.css";

type TransitionApi = {
  /** Show the duck loader, then navigate to `href`. */
  navigate: (href: string) => void;
  /** Show the duck loader around an in-page action (e.g. restarting the chat). */
  runWithLoader: (action: () => void) => void;
};

const TransitionContext = createContext<TransitionApi | null>(null);

const LOADER_LEAD_MS = 900;
const LOADER_TAIL_MS = 500;

export function TransitionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [visible, setVisible] = useState(false);
  const pendingPath = useRef<string | null>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const later = (fn: () => void, ms: number) => timers.current.push(setTimeout(fn, ms));
  const leadTime = () => (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 150 : LOADER_LEAD_MS);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  // Hide the loader once the new route has rendered.
  useEffect(() => {
    if (pendingPath.current && pendingPath.current === pathname) {
      pendingPath.current = null;
      later(() => setVisible(false), LOADER_TAIL_MS);
    }
  }, [pathname]);

  // Coming back through the back/forward cache must not leave the loader on screen.
  useEffect(() => {
    const onPageShow = (e: PageTransitionEvent) => e.persisted && setVisible(false);
    window.addEventListener("pageshow", onPageShow);
    return () => window.removeEventListener("pageshow", onPageShow);
  }, []);

  const navigate = useCallback(
    (href: string) => {
      const target = new URL(href, window.location.href);
      if (target.pathname === pathname) return;
      router.prefetch(target.pathname);
      pendingPath.current = target.pathname;
      setVisible(true);
      later(() => router.push(target.pathname + target.search + target.hash), leadTime());
    },
    [pathname, router]
  );

  const runWithLoader = useCallback((action: () => void) => {
    setVisible(true);
    later(() => {
      action();
      later(() => setVisible(false), LOADER_TAIL_MS);
    }, leadTime());
  }, []);

  const api = useMemo(() => ({ navigate, runWithLoader }), [navigate, runWithLoader]);

  return (
    <TransitionContext.Provider value={api}>
      {children}
      <div className={`${styles.loader} ${visible ? styles.visible : ""}`} role="status" aria-live="polite" aria-hidden={!visible}>
        {visible && <span className={styles.srOnly}>Загрузка</span>}
        <div className={styles.duck}>
          <Duck wingClassName={duckStyles.flap} />
        </div>
        <div className={styles.shadow} />
        <div className={styles.text}>
          Quack<span className={styles.accent}>!</span>
          <span className={styles.dots}>
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
        </div>
      </div>
    </TransitionContext.Provider>
  );
}

export function usePageTransition() {
  const api = useContext(TransitionContext);
  if (!api) throw new Error("usePageTransition must be used inside <TransitionProvider>");
  return api;
}
