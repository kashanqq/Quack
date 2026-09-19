// Typed calls for the domain endpoints. Types come from schema.d.ts (make types), so a backend
// change that breaks a caller fails the build instead of the screen.

import { api } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type BackendProgram = Schemas["Program"];
export type BackendMatch = Schemas["MatchOut"];
export type BackendMatching = Schemas["MatchingOut"];
export type BackendProfile = Schemas["Profile"];
export type BackendSaved = Schemas["SavedProgramWithProgram"];

export const backend = {
  profile: {
    get: () => api.get<BackendProfile>("/profile"),
    /** `path` is dotted, e.g. `academics.sat_score`; the server rejects unknown paths with 400 */
    patch: (path: string, value: unknown) =>
      api.patch<BackendProfile>("/profile", { path, value, by: "user" satisfies "user" }),
  },
  matching: {
    get: (limit = 50) => api.get<BackendMatching>(`/matching?limit=${limit}`),
    compare: (ids: string[]) => api.get<Schemas["CompareOut"]>(`/matching/compare?ids=${encodeURIComponent(ids.join(","))}`),
  },
  saved: {
    list: () => api.get<Schemas["Page_SavedProgramWithProgram_"]>("/saved"),
    add: (programId: string) => api.post<unknown>(`/saved/${encodeURIComponent(programId)}`),
    remove: (programId: string) => api.delete<void>(`/saved/${encodeURIComponent(programId)}`),
  },
};
