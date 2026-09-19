// Phase I5 Tasks Adapter: bridges backend /tasks and /sets topic lifecycle with frontend UI.

import {
  backend,
  type BackendAnswerResult,
  type BackendSetOut,
  type BackendTaskInstanceOut,
  type BackendTopicOut,
} from "@/api/backend";
import { type Task } from "./prepData";
import { REMOTE_PREP } from "./remoteSets";

const tasksCache = new Map<string, Task[]>();

export function adaptBackendTask(instance: BackendTaskInstanceOut): Task {
  return {
    id: instance.id,
    instanceId: instance.id,
    text: instance.stem_rendered,
    figure: instance.figure_url,
    options: instance.options.map((opt) => ({
      label: opt.text,
      key: opt.key,
    })),
  };
}

export async function fetchRemoteTopicTasks(
  skillId: string,
  setId?: string | null,
  count = 3
): Promise<Task[] | null> {
  if (!REMOTE_PREP) return null;

  const cacheKey = `${skillId}:${setId ?? ""}`;
  if (tasksCache.has(cacheKey)) {
    return tasksCache.get(cacheKey)!;
  }

  try {
    const tasks: Task[] = [];
    for (let i = 0; i < count; i++) {
      try {
        const instance = await backend.tasks.issue({
          skill_id: skillId,
          set_id: setId ?? null,
          mode: "topic",
          with_trap: null,
          exclude_seen: false,
        });
        tasks.push(adaptBackendTask(instance));
      } catch (err: unknown) {
        // If 404 on the first task, skill has no backend templates; fallback to local
        if (tasks.length === 0) {
          return null;
        }
        break;
      }
    }

    if (tasks.length > 0) {
      tasksCache.set(cacheKey, tasks);
      return tasks;
    }
    return null;
  } catch (err) {
    console.warn("Failed to fetch remote tasks for skill:", skillId, err);
    return null;
  }
}

export async function submitRemoteAnswer(
  instanceId: string,
  answerKey: string,
  timeSpentSec: number,
  mode = "topic"
): Promise<BackendAnswerResult> {
  return await backend.tasks.answer(instanceId, {
    answer: answerKey,
    time_spent_sec: Math.max(1, timeSpentSec),
    mode,
    after_guideline: false,
    hint_level_before: 0,
  });
}

export async function completeRemoteTopic(
  setId: string,
  skillId: string
): Promise<BackendSetOut | null> {
  try {
    return await backend.sets.topic.complete(setId, skillId);
  } catch (err) {
    console.warn("Failed to complete remote topic:", setId, skillId, err);
    return null;
  }
}

export async function openRemoteTopic(
  setId: string,
  skillId: string
): Promise<BackendTopicOut | null> {
  try {
    return await backend.sets.topic.open(setId, skillId);
  } catch (err) {
    console.warn("Failed to open remote topic:", setId, skillId, err);
    return null;
  }
}

export async function skipRemoteTask(
  instanceId: string,
  timeSpentSec: number,
  reason: "skipped" | "timed_out" = "skipped"
): Promise<void> {
  try {
    await backend.tasks.skip(instanceId, reason, Math.max(1, timeSpentSec));
  } catch (err) {
    console.warn("Failed to skip remote task:", instanceId, err);
  }
}

export function clearTasksCache(skillId?: string, setId?: string) {
  if (skillId) {
    tasksCache.delete(`${skillId}:${setId ?? ""}`);
  } else {
    tasksCache.clear();
  }
}
