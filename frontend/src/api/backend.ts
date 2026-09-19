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
export type BackendOverview = Schemas["OverviewOut"];
export type BackendMilestone = Schemas["MilestoneOut"];
export type BackendExamRequirement = Schemas["ExamRequirementOut"];
export type BackendExamProgress = Schemas["ExamProgress"];
export type BackendConflict = Schemas["ConflictOut"];
export type BackendKnowledgeVersion = Schemas["KnowledgeVersionOut"];
export type BackendSetsByExam = Schemas["SetsByExam"];
export type BackendSetOut = Schemas["SetOut"];
export type BackendTopicOut = Schemas["TopicOut"];
export type BackendSetProgress = Schemas["SetProgress"];
export type BackendTaskInstanceOut = Schemas["TaskInstanceOut"];
export type BackendOptionOut = Schemas["OptionOut"];
export type BackendTaskRequestIn = Schemas["TaskRequestIn"];
export type BackendAnswerIn = Schemas["AnswerIn"];
export type BackendAnswerResult = Schemas["AnswerResult"];
export type BackendTaskSkipIn = Schemas["TaskSkipIn"];

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
  overview: {
    get: () => api.get<BackendOverview>("/overview"),
    markMilestone: (key: string, done: boolean) =>
      api.post<BackendMilestone>(`/overview/milestones/${encodeURIComponent(key)}`, { done }),
  },
  sets: {
    list: (examId: "SAT_MATH" | "ENT_MATH") =>
      api.get<BackendSetsByExam>(`/sets?exam_id=${examId}`),
    switch: (setId: string) =>
      api.post<BackendSetsByExam>("/sets/switch", { set_id: setId }),
    get: (setId: string) =>
      api.get<BackendSetOut>(`/sets/${encodeURIComponent(setId)}`),
    open: (setId: string) =>
      api.post<BackendSetOut>(`/sets/${encodeURIComponent(setId)}/open`),
    patch: (setId: string, body: { skill_ids?: string[]; deadline?: string }) =>
      api.patch<BackendSetOut>(`/sets/${encodeURIComponent(setId)}`, body),
    topic: {
      open: (setId: string, skillId: string) =>
        api.post<BackendTopicOut>(`/sets/${encodeURIComponent(setId)}/topics/${encodeURIComponent(skillId)}/open`),
      complete: (setId: string, skillId: string) =>
        api.post<BackendSetOut>(`/sets/${encodeURIComponent(setId)}/topics/${encodeURIComponent(skillId)}/complete`),
    },
  },
  tasks: {
    issue: (body: BackendTaskRequestIn) =>
      api.post<BackendTaskInstanceOut>("/tasks", body),
    answer: (instanceId: string, body: Omit<BackendAnswerIn, "instance_id">) =>
      api.post<BackendAnswerResult>(`/tasks/${encodeURIComponent(instanceId)}/answer`, {
        instance_id: instanceId,
        ...body,
      }),
    skip: (instanceId: string, reason: "skipped" | "timed_out", timeSpentSec: number) =>
      api.post<void>(`/tasks/${encodeURIComponent(instanceId)}/skip`, {
        instance_id: instanceId,
        reason,
        time_spent_sec: timeSpentSec,
      }),
    solution: (instanceId: string) =>
      api.get<{ solution: string[] }>(`/tasks/${encodeURIComponent(instanceId)}/solution`),
  },
  prep: {
    version: () => api.get<BackendKnowledgeVersion>("/prep/knowledge/version"),
  },
};

