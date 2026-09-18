// Materials a student asks the assistant for inside a topic: notes (Markdown, can be saved as .md or
// PDF) and flashcards. Demo generation from the topic's content and the student's own traps and
// answers; the backend will generate the same shapes with a model (product-logic §4.4).

import type { ReactNode } from "react";
import { formatShort, skillById } from "./prepData";
import type { Material, PrepModel } from "./prepModel";
import { checksFor, TOPICS } from "./topicContent";

export type MaterialKind = Material["kind"];

/** What in a chat message asks for a material */
export function materialAsked(text: string): MaterialKind | null {
  const t = text.toLowerCase();
  if (/карточ/.test(t)) return "cards";
  if (/конспект/.test(t)) return "notes";
  return null;
}

const newId = (skillId: string, kind: MaterialKind) => `${skillId}-${kind}-${Date.now()}`;

/** Notes built around this student: the topic's minimum, their traps, what they got wrong */
export function generateNotes(model: PrepModel, skillId: string, count: number): Material {
  const skill = skillById(skillId);
  const content = TOPICS[skillId];
  const own = model.misconceptions[skillId].filter((m) => m.status === "confirmed" || m.status === "suspected");
  const wrong = model.evidence[skillId].filter((e) => /ловушка|неверно/.test(e.text)).slice(0, 3);
  const lines = [
    `# ${skill.name}`,
    `_Конспект · сделан ассистентом по твоему запросу · ${formatShort(new Date())}_`,
    "",
  ];
  if (content) {
    lines.push("## Суть", content.summary, "", "## Что нужно уметь", ...content.points.map((p) => `- ${p}`), "");
    lines.push("## Пример", `**Задача.** ${content.example.q}`, "", `**Решение.** ${content.example.a}`, "");
  }
  lines.push("## Где ошибаешься ты");
  if (own.length) lines.push(...own.map((m) => `- ${m.text}`));
  else lines.push("- Своих ловушек пока не видно.");
  if (content) lines.push(`- Частая у всех: ${content.trap.toLowerCase()}`);
  if (wrong.length) lines.push("", "## Твои последние ошибки", ...wrong.map((e) => `- ${e.text}`));
  const checks = checksFor(skillId).slice(0, 3);
  if (checks.length) lines.push("", "## Проверь себя", ...checks.map((t) => `- ${t.text}`));
  return {
    id: newId(skillId, "notes"),
    kind: "notes",
    title: count ? `Конспект ${count + 1}` : "Конспект",
    createdAt: new Date(),
    markdown: lines.join("\n"),
  };
}

/** Flashcards from the topic's questions, the student's traps and the worked example */
export function generateCards(model: PrepModel, skillId: string, count: number): Material {
  const content = TOPICS[skillId];
  const cards = checksFor(skillId).map((t) => {
    const right = t.options.find((o) => o.correct);
    const trap = t.options.find((o) => o.trap)?.trap;
    return { front: t.text, back: `${right?.label ?? "—"}${trap ? `\nЛовушка: ${trap.toLowerCase()}` : ""}` };
  });
  if (content) {
    cards.unshift({ front: content.example.q, back: content.example.a });
    content.points.forEach((p, i) => cards.push({ front: `Что нужно уметь · ${i + 1} из ${content.points.length}`, back: p }));
  }
  for (const m of model.misconceptions[skillId].filter((x) => x.status === "confirmed" || x.status === "suspected")) {
    cards.push({ front: "Твоя ловушка в этой теме", back: m.text });
  }
  return {
    id: newId(skillId, "cards"),
    kind: "cards",
    title: count ? `Карточки ${count + 1}` : "Карточки",
    createdAt: new Date(),
    cards,
  };
}

/* ---------- Markdown: the small part notes use — headings, lists, bold, italic ---------- */

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|_[^_]+_)/g).map((part, i) =>
    part.startsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part.startsWith("_") && part.endsWith("_") && part.length > 2 ? <em key={i}>{part.slice(1, -1)}</em> : part
  );
}

export function renderMarkdown(md: string): ReactNode[] {
  const out: ReactNode[] = [];
  let list: string[] = [];
  const flush = () => {
    if (!list.length) return;
    out.push(
      <ul key={`ul-${out.length}`}>
        {list.map((item, i) => (
          <li key={i}>{inline(item)}</li>
        ))}
      </ul>
    );
    list = [];
  };
  md.split("\n").forEach((line, i) => {
    if (line.startsWith("- ")) return void list.push(line.slice(2));
    flush();
    if (line.startsWith("# ")) out.push(<h1 key={i}>{inline(line.slice(2))}</h1>);
    else if (line.startsWith("## ")) out.push(<h2 key={i}>{inline(line.slice(3))}</h2>);
    else if (line.trim()) out.push(<p key={i}>{inline(line)}</p>);
  });
  flush();
  return out;
}

const escape = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function markdownToHtml(md: string) {
  const inl = (t: string) => escape(t).replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/_([^_]+)_/g, "<em>$1</em>");
  let html = "";
  let inList = false;
  for (const line of md.split("\n")) {
    if (line.startsWith("- ")) {
      if (!inList) html += "<ul>";
      inList = true;
      html += `<li>${inl(line.slice(2))}</li>`;
      continue;
    }
    if (inList) html += "</ul>";
    inList = false;
    if (line.startsWith("# ")) html += `<h1>${inl(line.slice(2))}</h1>`;
    else if (line.startsWith("## ")) html += `<h2>${inl(line.slice(3))}</h2>`;
    else if (line.trim()) html += `<p>${inl(line)}</p>`;
  }
  return inList ? `${html}</ul>` : html;
}

/** The notes as a .md file */
export function downloadMarkdown(title: string, md: string) {
  const url = URL.createObjectURL(new Blob([md], { type: "text/markdown;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title}.md`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** The notes as a PDF: a clean print page, saved through the browser's «Сохранить как PDF» */
export function printPdf(title: string, md: string) {
  const win = window.open("", "_blank");
  if (!win) return false;
  win.document.write(`<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>${escape(title)}</title>
<style>body{font:15px/1.55 system-ui,sans-serif;max-width:680px;margin:40px auto;padding:0 24px;color:#1f1d1b}
h1{font-size:26px;margin:0 0 4px}h2{font-size:17px;margin:22px 0 6px}em{color:#6b645e}ul{padding-left:20px}</style>
</head><body>${markdownToHtml(md)}</body></html>`);
  win.document.close();
  win.focus();
  win.print();
  return true;
}
