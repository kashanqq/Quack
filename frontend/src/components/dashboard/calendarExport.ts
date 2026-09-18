// Getting the dates out of Quack: a Google Calendar link per event and an .ics file with all of
// them (Google, Apple and Outlook all import .ics). No network, no account — everything is built
// in the browser from the dates the dashboard already computed.

import type { CalendarEvent } from "./dashboardRules";

const pad = (n: number) => String(n).padStart(2, "0");

/** All-day events use YYYYMMDD, with the end date one day after the start. */
const stamp = (d: Date) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
const nextDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1);

/** A link that opens Google Calendar with the event already filled in. */
export function googleCalendarUrl(event: CalendarEvent): string {
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: `Quack: ${event.title}`,
    dates: `${stamp(event.date)}/${stamp(nextDay(event.date))}`,
    details: `${event.detail}\n\nДата из Quack — сверься с сайтом вуза или экзамена.`,
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

const escape = (text: string) => text.replace(/([,;\\])/g, "\\$1").replace(/\n/g, "\\n");

/** One .ics with every date, for importing in a single go. */
export function icsFile(events: CalendarEvent[]): string {
  const now = `${stamp(new Date())}T000000Z`;
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Quack//Подготовка и подачи//RU",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Quack — даты поступления",
  ];

  for (const event of events) {
    lines.push(
      "BEGIN:VEVENT",
      `UID:${event.id.replace(/\s/g, "-")}@quack`,
      `DTSTAMP:${now}`,
      `DTSTART;VALUE=DATE:${stamp(event.date)}`,
      `DTEND;VALUE=DATE:${stamp(nextDay(event.date))}`,
      `SUMMARY:${escape(`Quack: ${event.title}`)}`,
      `DESCRIPTION:${escape(`${event.detail}\nДата из Quack — сверься с сайтом вуза или экзамена.`)}`,
      "TRANSP:TRANSPARENT",
      "END:VEVENT"
    );
  }

  lines.push("END:VCALENDAR");
  // The spec wants CRLF
  return lines.join("\r\n");
}

/** Hand the file to the browser; the student imports it into whatever calendar they use. */
export function downloadIcs(events: CalendarEvent[], name = "quack-dates.ics") {
  const blob = new Blob([icsFile(events)], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
