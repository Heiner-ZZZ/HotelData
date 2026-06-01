export function formatDateTime(value: string | null | undefined, locale = 'es-EC'): string {
  if (!value) {
    return 'N/D';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(parsed);
}
