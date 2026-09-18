"use client";

import { useEffect } from "react";

/**
 * A reload always starts at the top of the page. The browser would otherwise
 * restore the old scroll position (or jump to a #hash), which lands the reader
 * in the middle of the scroll-driven sections. Links that open a section on
 * purpose still work: only reloads are reset.
 */
export function ScrollToTopOnReload() {
  useEffect(() => {
    const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    if (nav?.type !== "reload") return;

    history.scrollRestoration = "manual";
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
    window.scrollTo(0, 0);
    // Late layout (images, fonts) can still move the page after hydration.
    const onLoad = () => window.scrollTo(0, 0);
    window.addEventListener("load", onLoad, { once: true });
    return () => window.removeEventListener("load", onLoad);
  }, []);

  return null;
}
