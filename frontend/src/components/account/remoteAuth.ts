// Sign-in against the backend (backend/app/api/auth.py). The session is the httpOnly cookie the server
// sets, so every call goes with credentials and the client never holds a token.

import { api, API_URL, ApiError } from "../../api/client";
import { AuthError, EMAIL_RE, PASSWORD_MIN, type AuthApi, type AuthErrorCode, type User } from "./contract";

type AuthOut = { student_id: string; email: string; name: string };

const toUser = (s: AuthOut): User => ({ id: s.student_id, email: s.email, name: s.name });

const CODES: Record<string, AuthErrorCode> = {
  unauthorized: "invalid",
  conflict: "exists",
  validation_failed: "email",
  too_many_requests: "rate",
};

/** Maps a backend error to what the login form knows how to show */
function fail(e: unknown): never {
  if (e instanceof AuthError) throw e;
  if (e instanceof ApiError) throw new AuthError(CODES[e.code] ?? "network");
  throw new AuthError("network");
}

export const remoteAuth: AuthApi = {
  async me() {
    try {
      return toUser(await api.get<AuthOut>("/auth/me"));
    } catch {
      return null;
    }
  },

  async login(email, password) {
    try {
      return toUser(await api.post<AuthOut>("/auth/login", { email: email.trim(), password }));
    } catch (e) {
      fail(e);
    }
  },

  async register(name, email, password) {
    if (!EMAIL_RE.test(email.trim())) throw new AuthError("email");
    if (password.length < PASSWORD_MIN) throw new AuthError("weak");
    try {
      return toUser(await api.post<AuthOut>("/auth/register", { name: name.trim(), email: email.trim(), password }));
    } catch (e) {
      fail(e);
    }
  },

  async loginWithGoogle(credential?: string) {
    if (credential) {
      try {
        return toUser(await api.post<AuthOut>("/auth/google", { credential }));
      } catch (e) {
        fail(e);
      }
    }
    // Not implemented on the backend yet (integration plan G3): fall back to the redirect flow,
    // which reports "network" if the endpoint is missing.
    if (typeof window !== "undefined") {
      window.location.assign(`${API_URL}/auth/google/login?next=${encodeURIComponent("/choice")}`);
      return new Promise<User>(() => {});
    }
    throw new AuthError("network");
  },

  async logout() {
    await api.post("/auth/logout").catch(() => undefined);
  },
};
