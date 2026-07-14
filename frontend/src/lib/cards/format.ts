const RU_MONTHS = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];

function parseDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  if (value instanceof Date) return value;
  const s = String(value);
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
  if (iso) {
    const d = new Date(Date.UTC(+iso[1], +iso[2] - 1, +iso[3]));
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const dmy = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(s);
  if (dmy) {
    const d = new Date(Date.UTC(+dmy[3], +dmy[2] - 1, +dmy[1]));
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDateRu(value: string | Date | null | undefined): string {
  const d = parseDate(value);
  if (!d) return "";
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${dd}.${mm}.${d.getUTCFullYear()}`;
}

export function formatDateRuLong(value: string | Date | null | undefined): string {
  const d = parseDate(value);
  if (!d) return "";
  const month = RU_MONTHS[d.getUTCMonth()];
  if (!month) return "";
  return `${d.getUTCDate()} ${month} ${d.getUTCFullYear()}`;
}

export function yearOf(value: string | Date | null | undefined): string {
  const d = parseDate(value);
  return d ? String(d.getUTCFullYear()) : "";
}
