"use client";

import { useState } from "react";
import { ChoiceApp } from "./ChoiceApp";

/** Remounts the chat from scratch when the user picks "Начать заново". */
export function ChoiceRoot() {
  const [session, setSession] = useState(0);
  return <ChoiceApp key={session} onRestart={() => setSession((s) => s + 1)} />;
}
