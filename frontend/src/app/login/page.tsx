import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginView } from "@/components/account/LoginView";

export const metadata: Metadata = {
  title: "Quack! — Вход",
};

export default function LoginPage() {
  // useSearchParams needs a boundary, or the whole page renders on the client only
  return (
    <Suspense>
      <LoginView />
    </Suspense>
  );
}
