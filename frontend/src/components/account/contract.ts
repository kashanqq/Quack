// The account contract: who is signed in, and the per-student state the client keeps between visits.
// Today both live in the browser (local*.ts); with NEXT_PUBLIC_DATA_SOURCE=remote they go to the backend
// (remote*.ts). Screens only ever see these types, so switching is one environment variable.
//
// Backend endpoints the remote side expects (FastAPI, cookie `quack_token`, `credentials: "include"`):
//   POST   /auth/login     {email, password}        → 200 {student_id, email, name} | 401 | 429   (exists)
//   GET    /auth/me                                  → 200 {student_id, email, name} | 401         (exists)
//   POST   /auth/logout                              → 204                                         (exists)
//   POST   /auth/register  {email, password, name}   → 201 {student_id, email, name} | 409         (to add)
//   GET    /auth/google/login?next=...               → 302 Redirect to Google OAuth                (to add)
//   POST   /auth/google    {credential}              → 200 {student_id, email, name}               (to add)
//   GET    /state                                    → 200 {[key]: value}                          (to add)
//   PATCH  /state          {[key]: value | null}     → 204, null deletes the key                   (to add)
//   DELETE /state                                    → 204, "начать заново"                        (to add)

export type User = {
  id: string;
  email: string;
  /** How the student is addressed; the backend keeps it in the profile */
  name: string;
};

export type AuthErrorCode = "invalid" | "exists" | "weak" | "email" | "rate" | "network";

export class AuthError extends Error {
  constructor(public code: AuthErrorCode) {
    super(code);
  }
}

export interface AuthApi {
  /** The signed-in student, or null. Called once when an app page opens */
  me(): Promise<User | null>;
  login(email: string, password: string): Promise<User>;
  register(name: string, email: string, password: string): Promise<User>;
  /** Sign in via Google account (credential token from GIS or OAuth redirect) */
  loginWithGoogle(credential?: string): Promise<User>;
  logout(): Promise<void>;
}

/** Where the per-student state is kept. The cache in front of it lives in store.ts */
export interface StateBackend {
  /** Everything stored for this student, loaded once per visit */
  load(userId: string): Promise<Record<string, unknown>>;
  /** A batch of changed keys; null removes a key */
  save(userId: string, entries: Record<string, unknown>): Promise<void>;
  /** The same, but it has to survive the tab closing right after */
  saveOnExit(userId: string, entries: Record<string, unknown>): void;
  clear(userId: string): Promise<void>;
}

/** Password rules shared by the form and the local stand-in; the backend checks its own */
export const PASSWORD_MIN = 8;
export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
