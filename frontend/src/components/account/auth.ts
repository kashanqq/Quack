import type { AuthApi } from "./contract";
import { localAuth } from "./localAuth";
import { remoteAuth } from "./remoteAuth";

/** Sign-in in this browser for now; NEXT_PUBLIC_DATA_SOURCE=remote sends it to the backend */
export const auth: AuthApi = process.env.NEXT_PUBLIC_DATA_SOURCE === "remote" ? remoteAuth : localAuth;
