/**
 * Global patch for Syncfusion DatePicker: updateMinMaxDateToEditor
 * crashes with "Cannot read properties of undefined (reading 'querySelector')"
 * when the picker has no element (showHeaderBar=false, or not yet rendered)
 * and selectedDate is changed via API (goToday).
 *
 * Loaded in main.ts — uses dynamic import so the calendars bundle is NOT
 * pulled into the main chunk (keeps initial budget <1.5MB). The patch runs
 * async before any lazy chunk needs it; per-instance guard in
 * reception-timeline covers the race.
 */
(async () => {
  try {
    const { DatePicker } = await import('@syncfusion/ej2-calendars');
    const proto = (DatePicker as unknown as { prototype: { updateMinMaxDateToEditor?: (...a: unknown[]) => unknown; __hgGuarded?: boolean } })?.prototype;
    if (proto && typeof proto.updateMinMaxDateToEditor === 'function' && !proto.__hgGuarded) {
      const orig = proto.updateMinMaxDateToEditor as (...a: unknown[]) => unknown;
      proto.updateMinMaxDateToEditor = function (this: { element?: unknown; inputElement?: unknown }, ...args: unknown[]) {
        try {
          if (!this.element || !this.inputElement) return;
          return (orig as (...a: unknown[]) => unknown).apply(this, args);
        } catch {
          return;
        }
      } as unknown as typeof proto.updateMinMaxDateToEditor;
      proto.__hgGuarded = true;
    }
  } catch {
    // Fallback per-instance guard in reception-timeline will handle it.
  }
})();
