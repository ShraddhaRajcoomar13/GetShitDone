export const SAST = "Africa/Johannesburg";

/** Today's date in SAST, as "YYYY-MM-DD". Always correct regardless of browser tz. */
export function todayISO(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: SAST, year: "numeric", month: "2-digit", day: "2-digit",
  }).format(new Date());
}

/** The Monday of the current SAST week, as "YYYY-MM-DD". */
export function mondayISO(): string {
  const iso = todayISO();
  const d = new Date(iso + "T00:00:00Z");
  const offset = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - offset);
  return d.toISOString().slice(0, 10);
}

/** Parse a backend-ISO string as SAST-naive (backend omits tz suffix). */
function parseSast(iso: string): Date {
  if (iso.includes("Z") || /[+-]\d{2}:\d{2}$/.test(iso)) return new Date(iso);
  return new Date(iso + "+02:00");
}

/** Extract HH:MM from a backend ISO string without timezone pitfalls. */
export function hourMinuteFromIso(iso: string | null | undefined): { hh: number; mm: number } {
  if (!iso) return { hh: 9, mm: 0 };
  return {
    hh: Number(iso.slice(11, 13)),
    mm: Number(iso.slice(14, 16)),
  };
}

/** Build a backend-ISO string from a SAST wall-clock time. */
export function sastToBackendIso(
  year: number, month: number, day: number, hh: number, mm: number,
): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${year}-${pad(month)}-${pad(day)}T${pad(hh)}:${pad(mm)}:00`;
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "unscheduled";
  return parseSast(iso).toLocaleTimeString("en-ZA", {
    timeZone: SAST, hour: "2-digit", minute: "2-digit",
  });
}

export function fmtDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = {}): string {
  if (!iso) return "";
  return parseSast(iso).toLocaleDateString("en-ZA", {
    timeZone: SAST, month: "short", day: "numeric", ...opts,
  });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return parseSast(iso).toLocaleString("en-ZA", {
    timeZone: SAST, month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

/** Pretty weekday label from a plain YYYY-MM-DD string, rendered in SAST. */
export function fmtWeekday(iso: string): string {
  return new Date(iso + "T12:00:00Z").toLocaleDateString("en-ZA", {
    timeZone: SAST, weekday: "short", month: "short", day: "numeric",
  });
}