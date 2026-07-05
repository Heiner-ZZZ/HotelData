export function todayIso(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

export function shiftDate(iso: string, days: number): string {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
