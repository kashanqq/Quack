"use client";

import { useState } from "react";
import { AuthGate } from "@/components/account/AuthGate";
import { HelpProvider } from "@/components/hints/FirstHint";
import { ChoiceApp } from "./ChoiceApp";

/** Opens for a signed-in student only; remounts the chat from scratch on "Начать заново". */
export function ChoiceRoot() {
  const [session, setSession] = useState(0);
  return (
    <AuthGate>
      {/* Screens hand their explanation to the walking help duck through this */}
      <HelpProvider>
        <ChoiceApp key={session} onRestart={() => setSession((s) => s + 1)} />
      </HelpProvider>
    </AuthGate>
  );
}
