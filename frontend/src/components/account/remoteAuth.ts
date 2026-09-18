// Sign-in against the backend (backend/app/api/auth.py). The session is the httpOnly cookie the server
// sets, so every call goes with credentials and the client never holds a token.

import { AuthError, type AuthApi, type User } from "./contract";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type StudentCtx = { student_id: string; email: string; name?: string };

const toUser = (s: StudentCtx): User => ({ id: s.student_id, email: s.email, name: s.name ?? s.email.split("@")[0] });

async function call(path: string, body?: unknown) {
  try {
    return await fetch(`${API}${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "include",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new AuthError("network");
  }
}

function fail(status: number): never {
  if (status === 401) throw new AuthError("invalid");
  if (status === 409) throw new AuthError("exists");
  if (status === 422) throw new AuthError("email");
  if (status === 429) throw new AuthError("rate");
  throw new AuthError("network");
}

export const remoteAuth: AuthApi = {
  async me() {
    const res = await call("/auth/me").catch(() => null);
    return res?.ok ? toUser(await res.json()) : null;
  },

  async login(email, password) {
    const res = await call("/auth/login", { email: email.trim(), password });
    if (!res.ok) fail(res.status);
    return toUser(await res.json());
  },

  async register(name, email, password) {
    const res = await call("/auth/register", { name: name.trim(), email: email.trim(), password });
    if (!res.ok) fail(res.status);
    return toUser(await res.json());
  },

  async logout() {
    await call("/auth/logout", {}).catch(() => undefined);
  },
};
