"use client";

import { flushSync } from "react-dom";

type ViewTransition = { finished?: Promise<void>; ready?: Promise<void>; updateCallbackDone?: Promise<void> };
type WithViewTransition = Document & { startViewTransition?: (callback: () => void) => ViewTransition };

/**
 * Switch sections through the View Transitions API, so shared elements slide into their new place
 * instead of blinking. Falls back to a plain update where the API is missing or motion is reduced.
 */
export function morph(update: () => void) {
  const doc = document as WithViewTransition;
  if (!doc.startViewTransition || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    update();
    return;
  }

  // The browser runs the callback on its next frame; if frames are throttled (hidden pane,
  // background tab) the interface must not wait for one, so a timer applies the update anyway.
  let applied = false;
  const apply = () => {
    if (applied) return;
    applied = true;
    flushSync(update);
  };
  const timer = setTimeout(apply, 120);

  try {
    const transition = doc.startViewTransition(() => {
      clearTimeout(timer);
      apply();
    });
    // Clicking again before the previous move ends skips it; that rejection is expected, not a fault
    const hush = () => {};
    transition?.finished?.catch(hush);
    transition?.ready?.catch(hush);
    transition?.updateCallbackDone?.catch(hush);
  } catch {
    clearTimeout(timer);
    apply();
  }
}
