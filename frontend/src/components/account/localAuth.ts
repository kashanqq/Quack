// Accounts kept in this browser, standing in for the backend's users table. Passwords are never stored:
// PBKDF2 with a random salt, the same kind of check the server does with bcrypt. This is not security —
// anyone with the device can read localStorage — only a way to exercise sign-in, sessions and
// per-student data before the backend is up.

import { AuthError, EMAIL_RE, PASSWORD_MIN, type AuthApi, type User } from "./contract";

const ACCOUNTS_KEY = "quack-accounts";
/** Device-level: which account this browser is signed in as. The backend uses an httpOnly cookie */
const SESSION_KEY = "quack-session";
const ITERATIONS = 120_000;

type Account = User & { salt: string; hash: string; createdAt: string };

const toHex = (bytes: ArrayBuffer | Uint8Array) =>
  [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");

async function derive(password: string, salt: string) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt: new TextEncoder().encode(salt), iterations: ITERATIONS },
    key,
    256
  );
  return toHex(bits);
}

function accounts(): Account[] {
  try {
    const list = JSON.parse(localStorage.getItem(ACCOUNTS_KEY) ?? "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

const publicPart = ({ id, email, name }: Account): User => ({ id, email, name });
const normalize = (email: string) => email.trim().toLowerCase();

function startSession(account: Account) {
  try {
    localStorage.setItem(SESSION_KEY, account.id);
  } catch {}
  return publicPart(account);
}

// A server takes a moment to answer, never zero: keeps the form's busy state honest
const pause = () => new Promise((r) => setTimeout(r, 250));

export const localAuth: AuthApi = {
  async me() {
    try {
      const id = localStorage.getItem(SESSION_KEY);
      const account = id ? accounts().find((a) => a.id === id) : undefined;
      return account ? publicPart(account) : null;
    } catch {
      return null;
    }
  },

  async login(email, password) {
    await pause();
    const account = accounts().find((a) => a.email === normalize(email));
    // The same answer for an unknown email and a wrong password, as the backend gives
    if (!account || (await derive(password, account.salt)) !== account.hash) throw new AuthError("invalid");
    return startSession(account);
  },

  async register(name, email, password) {
    await pause();
    const address = normalize(email);
    if (!EMAIL_RE.test(address)) throw new AuthError("email");
    if (password.length < PASSWORD_MIN) throw new AuthError("weak");
    const list = accounts();
    if (list.some((a) => a.email === address)) throw new AuthError("exists");

    const salt = toHex(crypto.getRandomValues(new Uint8Array(16)));
    const account: Account = {
      id: crypto.randomUUID(),
      email: address,
      name: name.trim() || address.split("@")[0],
      salt,
      hash: await derive(password, salt),
      createdAt: new Date().toISOString(),
    };
    try {
      localStorage.setItem(ACCOUNTS_KEY, JSON.stringify([...list, account]));
    } catch {
      throw new AuthError("network");
    }
    return startSession(account);
  },

  async loginWithGoogle() {
    await pause();
    const address = "alexey.smirnov@gmail.com";
    const list = accounts();
    let account = list.find((a) => a.email === address);
    if (!account) {
      account = {
        id: crypto.randomUUID(),
        email: address,
        name: "Алексей Смирнов",
        salt: "google-mock-salt",
        hash: "google-mock-hash",
        createdAt: new Date().toISOString(),
      };
      try {
        localStorage.setItem(ACCOUNTS_KEY, JSON.stringify([...list, account]));
      } catch {
        throw new AuthError("network");
      }
    }
    return startSession(account);
  },

  async logout() {
    try {
      localStorage.removeItem(SESSION_KEY);
    } catch {}
  },
};
