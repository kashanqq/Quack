"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { PixelDuck } from "@/components/duck/PixelDuck";
import { auth } from "./auth";
import { AuthError, EMAIL_RE, PASSWORD_MIN, type AuthErrorCode } from "./contract";
import { store } from "./store";
import styles from "./account.module.css";

type Mode = "login" | "signup";

const ERRORS: Record<AuthErrorCode, string> = {
  invalid: "Неверная почта или пароль",
  exists: "Эта почта уже зарегистрирована. Попробуй войти",
  weak: `Пароль должен быть не короче ${PASSWORD_MIN} символов`,
  email: "Проверь почту: похоже, в ней опечатка",
  rate: "Слишком много попыток. Подожди минуту",
  network: "Не получилось связаться с сервером. Попробуй ещё раз",
};

/** Only paths inside the app, so a crafted link cannot send the student elsewhere after sign-in */
const safeNext = (next: string | null) => (next && next.startsWith("/") && !next.startsWith("//") ? next : "/choice");

/** Sign-in and sign-up on one card: the same three fields, the name only for a new account. */
export function LoginView() {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const [mode, setMode] = useState<Mode>(params.get("mode") === "signup" ? "signup" : "login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Already signed in: straight on
  useEffect(() => {
    auth.me().then((me) => me && router.replace(next));
  }, [next, router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!EMAIL_RE.test(email.trim())) return setError(ERRORS.email);
    if (mode === "signup" && password.length < PASSWORD_MIN) return setError(ERRORS.weak);

    setBusy(true);
    setError(null);
    try {
      const user = mode === "signup" ? await auth.register(name, email, password) : await auth.login(email, password);
      await store.open(user);
      router.replace(next);
    } catch (err) {
      setError(ERRORS[err instanceof AuthError ? err.code : "network"]);
      setBusy(false);
    }
  }

  const switchTo = (to: Mode) => {
    setMode(to);
    setError(null);
  };

  return (
    <main className={styles.page}>
      <form className={styles.card} onSubmit={onSubmit} noValidate>
        <Link href="/" className={styles.brand} aria-label="Quack! — на главную">
          <PixelDuck tempo="steady" className={styles.brandDuck} />
          <span>
            Quack<span className={styles.accent}>!</span>
          </span>
        </Link>

        <div className={styles.switch} role="tablist" aria-label="Вход или регистрация">
          <button type="button" role="tab" aria-selected={mode === "login"} onClick={() => switchTo("login")}>
            Вход
          </button>
          <button type="button" role="tab" aria-selected={mode === "signup"} onClick={() => switchTo("signup")}>
            Регистрация
          </button>
        </div>

        {mode === "signup" && (
          <label className={styles.field}>
            <span>Как тебя зовут</span>
            <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" placeholder="Имя" />
          </label>
        )}
        <label className={styles.field}>
          <span>Почта</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            placeholder="you@example.com"
            required
            autoFocus
          />
        </label>
        <label className={styles.field}>
          <span>Пароль</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            placeholder={mode === "signup" ? `Не короче ${PASSWORD_MIN} символов` : ""}
            required
          />
        </label>

        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}

        <button className={styles.submit} type="submit" disabled={busy || !email || !password}>
          {busy ? "Секунду…" : mode === "signup" ? "Создать аккаунт" : "Войти"}
        </button>

        <p className={styles.note}>
          {process.env.NEXT_PUBLIC_DATA_SOURCE === "remote"
            ? "Вход через Google появится позже."
            : "Пока нет сервера, аккаунт хранится только в этом браузере. Вход через Google появится позже."}
        </p>
      </form>
    </main>
  );
}
