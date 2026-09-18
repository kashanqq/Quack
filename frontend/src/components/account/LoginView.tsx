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

  async function onGoogleLogin() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const user = await auth.loginWithGoogle();
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

        <button
          className={styles.googleBtn}
          type="button"
          onClick={onGoogleLogin}
          disabled={busy}
          aria-label="Продолжить с Google"
        >
          <svg className={styles.googleIcon} viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="#4285F4"
              d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
            />
            <path
              fill="#34A853"
              d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24z"
            />
            <path
              fill="#FBBC05"
              d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.16 0 9.97 0 12s.45 3.84 1.25 5.42l4.03-3.15z"
            />
            <path
              fill="#EA4335"
              d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
            />
          </svg>
          <span>{busy ? "Подключение…" : "Продолжить с Google"}</span>
        </button>

        <div className={styles.divider} aria-hidden="true">
          <span>или через почту</span>
        </div>

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
            ? "Авторизация через сервер Quack! API."
            : "Вход через Google работает в режиме демо-аккаунта. Данные синхронизируются локально."}
        </p>
      </form>
    </main>
  );
}
