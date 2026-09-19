// Phase I5 Sets Adapter: bridges backend /sets routes with frontend UI models.

import {
  backend,
  type BackendSetOut,
  type BackendSetsByExam,
  type BackendTopicOut,
} from "@/api/backend";
import {
  registerRemoteSets,
  registerRemoteSkills,
  TODAY,
  type ExamId,
  type Skill,
  type StudySet,
} from "./prepData";
import { parseIsoDate, toBackendExamId } from "./remotePrep";

export const REMOTE_PREP =
  process.env.NEXT_PUBLIC_SRC_PREP === "remote" ||
  process.env.NEXT_PUBLIC_DATA_SOURCE === "remote";

export type RemoteSetsData = {
  current: StudySet | null;
  upcoming: StudySet[];
  done: StudySet[];
  raw?: BackendSetsByExam;
};

const SETS_CACHE_PREFIX = "quack:prep:sets-cache:";
const memoryCache = new Map<ExamId, RemoteSetsData>();
const inFlightRequests = new Map<ExamId, Promise<RemoteSetsData>>();

export function adaptBackendSet(raw: BackendSetOut, exam: ExamId): StudySet {
  // Register skills from topics into the dynamic registry so skillById resolves them
  if (raw.topics && raw.topics.length > 0) {
    const adaptedSkills: Skill[] = raw.topics.map((t: BackendTopicOut) => ({
      id: t.skill_id,
      name: t.name,
      area: raw.area_ids?.[0] ?? "Алгебра",
      exam,
      weight: 5,
      state: t.level === "solid" || t.level === "closed" ? "solid" : t.level === "shaky" ? "shaky" : "weak",
      recall: t.level === "solid" ? 0.8 : t.level === "shaky" ? 0.6 : 0.4,
      requires: [],
      root: t.is_root,
      misconceptions: (t.misconception_labels || []).map((lbl) => ({
        id: lbl,
        text: lbl,
        status: "suspected" as const,
        observations: 1,
      })),
      evidence: [],
    }));
    registerRemoteSkills(adaptedSkills);
  }

  let title = raw.reason;
  if (raw.kind === "consolidation") {
    title = "Закрепление перед тестом";
  } else if (raw.kind === "review") {
    title = "Повторение навыков";
  } else if (raw.topics && raw.topics.length > 0) {
    title = raw.topics[0].name;
    if (raw.topics.length > 1) {
      title += ` и ещё ${raw.topics.length - 1}`;
    }
  }

  const studySet: StudySet = {
    id: raw.id,
    rawId: raw.id,
    exam,
    number: raw.position + 1,
    title: title || `Сет ${raw.position + 1}`,
    area: raw.area_ids?.[0] || "Алгебра",
    skills: (raw.topics || []).map((t) => t.skill_id),
    start: raw.opened_at ? parseIsoDate(raw.opened_at) : TODAY,
    deadline: parseIsoDate(raw.deadline),
    status:
      raw.status === "current"
        ? "current"
        : raw.status === "done"
        ? "done"
        : raw.kind === "review"
        ? "review"
        : "upcoming",
    why: raw.reason,
    kind: raw.kind,
    topics: raw.topics,
    progress: raw.progress,
  };

  return studySet;
}

function reviveSetsData(raw: unknown, exam: ExamId): RemoteSetsData | null {
  if (!raw || typeof raw !== "object") return null;
  try {
    const data = raw as { current: unknown; upcoming: unknown[]; done: unknown[] };
    const current = data.current ? reviveSet(data.current, exam) : null;
    const upcoming = Array.isArray(data.upcoming) ? data.upcoming.map((s) => reviveSet(s, exam)) : [];
    const done = Array.isArray(data.done) ? data.done.map((s) => reviveSet(s, exam)) : [];

    const all = [...(current ? [current] : []), ...upcoming, ...done];
    registerRemoteSets(all);

    return { current, upcoming, done };
  } catch (err) {
    console.warn("Failed to revive cached sets data:", err);
    return null;
  }
}

function reviveSet(raw: unknown, exam: ExamId): StudySet {
  const s = raw as StudySet;
  return {
    ...s,
    exam,
    start: s.start ? new Date(s.start) : TODAY,
    deadline: s.deadline ? new Date(s.deadline) : TODAY,
  };
}

export function getCachedRemoteSets(exam: ExamId): RemoteSetsData | null {
  if (memoryCache.has(exam)) {
    return memoryCache.get(exam)!;
  }
  if (typeof window === "undefined") return null;
  try {
    const item = window.localStorage.getItem(`${SETS_CACHE_PREFIX}${exam}`);
    if (item) {
      const parsed = JSON.parse(item);
      const revived = reviveSetsData(parsed, exam);
      if (revived) {
        memoryCache.set(exam, revived);
        return revived;
      }
    }
  } catch (e) {
    console.warn("Failed to read cached sets from localStorage", e);
  }
  return null;
}

export function saveCachedRemoteSets(exam: ExamId, data: RemoteSetsData) {
  memoryCache.set(exam, data);
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(`${SETS_CACHE_PREFIX}${exam}`, JSON.stringify(data));
  } catch (e) {
    console.warn("Failed to write sets to localStorage", e);
  }
}

export async function fetchRemoteSets(exam: ExamId, forceRefresh = false): Promise<RemoteSetsData> {
  if (!forceRefresh) {
    const cached = getCachedRemoteSets(exam);
    if (cached) return cached;
  }

  if (inFlightRequests.has(exam)) {
    return inFlightRequests.get(exam)!;
  }

  const backendExam = toBackendExamId(exam);
  const promise = (async () => {
    try {
      const res = await backend.sets.list(backendExam);
      const current = res.current ? adaptBackendSet(res.current, exam) : null;
      const upcoming = (res.upcoming || []).map((s) => adaptBackendSet(s, exam));
      const done = (res.done || []).map((s) => adaptBackendSet(s, exam));

      const all = [...(current ? [current] : []), ...upcoming, ...done];
      registerRemoteSets(all);

      const result: RemoteSetsData = {
        current,
        upcoming,
        done,
        raw: res,
      };

      saveCachedRemoteSets(exam, result);
      return result;
    } finally {
      inFlightRequests.delete(exam);
    }
  })();

  inFlightRequests.set(exam, promise);
  return promise;
}

export function prefetchRemoteSets(exam: ExamId) {
  fetchRemoteSets(exam).catch((err) => {
    console.warn("Failed to prefetch remote sets for", exam, err);
  });
}

export async function switchRemoteSet(setId: string, exam: ExamId): Promise<RemoteSetsData> {
  const res = await backend.sets.switch(setId);
  const current = res.current ? adaptBackendSet(res.current, exam) : null;
  const upcoming = (res.upcoming || []).map((s) => adaptBackendSet(s, exam));
  const done = (res.done || []).map((s) => adaptBackendSet(s, exam));

  const all = [...(current ? [current] : []), ...upcoming, ...done];
  registerRemoteSets(all);

  const result: RemoteSetsData = {
    current,
    upcoming,
    done,
    raw: res,
  };

  saveCachedRemoteSets(exam, result);
  return result;
}

export async function openRemoteSet(setId: string, exam: ExamId): Promise<StudySet> {
  const res = await backend.sets.open(setId);
  const adapted = adaptBackendSet(res, exam);
  registerRemoteSets([adapted]);
  // Refetch exam sets to update active state
  fetchRemoteSets(exam, true).catch(() => {});
  return adapted;
}
