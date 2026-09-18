"use client";

import { useState } from "react";
import { AuthGate } from "@/components/account/AuthGate";
import { ChoiceApp } from "./ChoiceApp";

/** Opens for a signed-in student only; remounts the chat from scratch on "Начать заново". */
export function ChoiceRoot() {
  const [session, setSession] = useState(0);
  return (
    <AuthGate>
      <ChoiceApp key={session} onRestart={() => setSession((s) => s + 1)} />
    </AuthGate>
  );
}
