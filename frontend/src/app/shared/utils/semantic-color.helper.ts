/**
 * Semantic color helper — the bridge between the design-token system
 * (`frontend/src/styles/_scss-variables.scss`) and TypeScript code
 * that needs to **render** colors outside of SCSS partials.
 *
 * Use this when:
 *  - building a chart dataset for `chart.js` / `ng2-charts`,
 *  - setting `[style.color]` / `[style.background]` in templates,
 *  - composing a MapLibre marker HTML string,
 *  - returning a CSS color expression from a status-code map,
 *  - or any other runtime path that previously hardcoded a hex
 *    like `#22c55e` or a raw `rgba(...)` literal.
 *
 * Three exports.
 *
 *  1. {@link PALETTE_STATUS_MAP} — status code → CSS-var reference.
 *     FROZEN literal object (`as const`) so dot-access on known keys
 *     (`PALETTE_STATUS_MAP.muted`) and bracket-access on dynamic
 *     strings (`PALETTE_STATUS_MAP[status]`) both compile without
 *     the TS4111 "Property comes from an index signature" workaround.
 *
 *  2. {@link statusColor} — runtime helper normalising input to
 *     lowercase, falling back to {@link STATUS_COLOR_FALLBACK} when
 *     status is null/empty/unmapped.
 *
 *  3. {@link withAlpha} — composes a `color-mix(in srgb, ${token}
 *     ${pct}%, transparent)` string so callers can vary opacity
 *     without introducing a new hex literal. Pulls the token literal
 *     up-front so the browser resolves the underlying var at
 *     paint time, which keeps light/dark theme switching free.
 *
 *  Hex literals **do not belong** in this file. Every color resolves
 *  through the CSS custom property cascade, so a single theme toggle
 *  on `<html data-theme="dark">` lifts or dims every consumer at
 *  once. To extend, add a new key in
 *  `_scss-variables.scss :root` AND `[data-theme="dark"]` and
 *  reference it via `var(--new-token)` from this file.
 *
 * ── EXTENSION RULE for PALETTE_STATUS_MAP ──
 *
 *  - Status keys are **lowercase strings, no spaces**. New status
 *    codes should normalise via `status.toLowerCase()` before lookup.
 *  - **snake_case** is preferred for multi-word codes
 *    (`checked_out`, `cleaning_in_progress`) — keep aligned with
 *    server-side state machine values in
 *    `server/src/app/core/state_machine.py`.
 *  - When adding a key, pick the closest semantic token by visual
 *    family (success / warning / danger / accent / muted). If a
 *    status doesn't fit any, ask a designer before introducing a new
 *    theme token.
 *
 * ── CANVAS CAVEAT ──
 *
 *  Chart libraries (`chart.js`, `ng2-charts`, native canvas, MapLibre
 *  custom layers) read colors **at JS-time** — a string `'var(--x)'`
 *  is NOT resolved by the canvas API. For those, follow the pattern
 *  in `expenses-dashboard-page.ts`:
 *
 *     const muted = getComputedStyle(root).getPropertyValue('--muted-text').trim();
 *
 *  This helper is safe for **HTML inline styles** (Angular `[style]`,
 *  template `style="..."`) and any `[ngStyle]` consumer that runs
 *  through CSS resolution.
 */

// ────────────────────────────────────────────────────────────────────
// Semantic token catalogue
// ────────────────────────────────────────────────────────────────────

/**
 * Union of every `--*` token we currently bind semantic meaning to.
 * Picked from the canonical set in `_scss-variables.scss`. Used by
 * withAlpha to type-check that callers don't pass arbitrary strings,
 * but the underlying function accepts `string` as well — widen as
 * needed by importing a richer palette.
 */
export type SemanticToken =
  | '--success' | '--success-strong' | '--success-light'
  | '--warning' | '--warning-strong' | '--warning-light'
  | '--danger' | '--danger-strong' | '--danger-light'
  | '--accent' | '--accent-strong' | '--accent-light'
  | '--cyan' | '--teal'
  | '--purple' | '--purple-strong' | '--purple-light'
  | '--indigo' | '--indigo-strong' | '--indigo-light'
  | '--yellow'
  | '--muted-text'
  | '--gray-50' | '--gray-100' | '--gray-200' | '--gray-300'
  | '--gray-400' | '--gray-500' | '--gray-600' | '--gray-700' | '--gray-800' | '--gray-900'
  | '--surface' | '--surface-raised' | '--surface-soft';

// ────────────────────────────────────────────────────────────────────
// Status → color map
// ────────────────────────────────────────────────────────────────────

/**
 * Status code → CSS color expression. Each value is a `var(--token)`
 * reference so light/dark theme switching cascades automatically.
 *
 * Keys are **lowercase strings** — normalise input before lookup.
 * snake_case preferred for multi-word codes (mirrors server state
 * machine names).
 */
export const PALETTE_STATUS_MAP = Object.freeze({
  // ── Success family (green) ──
  active: 'var(--success)',
  confirmed: 'var(--success)',
  paid: 'var(--success)',
  success: 'var(--success)',
  completed: 'var(--success)',
  ok: 'var(--success)',
  available: 'var(--success)',
  done: 'var(--success)',
  done_clean: 'var(--success)',
  checked_in: 'var(--success)',
  checked_out_paid: 'var(--success)',
  occupied: 'var(--success)',

  // ── Accent / brand (blue) ──
  reserved: 'var(--accent)',
  in_progress: 'var(--accent)',
  in_cleaning: 'var(--accent)',
  info: 'var(--accent)',

  // ── Warning family (amber) ──
  pending: 'var(--warning)',
  upcoming: 'var(--warning)',
  partially_paid: 'var(--warning)',
  attention: 'var(--warning)',
  maintenance: 'var(--warning)',
  scheduled: 'var(--warning)',
  dirty: 'var(--warning)',

  // ── Danger family (red) ──
  cancelled: 'var(--danger)',
  failed: 'var(--danger)',
  overdue: 'var(--danger)',
  rejected: 'var(--danger)',
  error: 'var(--danger)',
  out_of_order: 'var(--danger)',
  blocked: 'var(--danger)',

  // ── Cyan/info (cyan) ──
  informational: 'var(--cyan)',

  // ── Purple (special entities like room type / policy) ──
  inspection: 'var(--purple-strong)',
  special: 'var(--purple-strong)',

  // ── Muted / archive ──
  archived: 'var(--gray-600)',
  inactive: 'var(--gray-500)',
  past: 'var(--gray-600)',

  // ── Default fallback (last key by convention) ──
  muted: 'var(--muted-text)',
} as const);

/**
 * Type of the status map indices — derived from the frozen object
 * literal so it's always in sync with PALETTE_STATUS_MAP keys.
 * Used internally for the index-typed bracket access below.
 */
type StatusKey = keyof typeof PALETTE_STATUS_MAP;

/**
 * Default fallback color when status is null/empty/unmapped.
 *
 * Exported as a separate const so callers needing the muted token
 * reference don't have to touch PALETTE_STATUS_MAP (which would put
 * them into the `Record<string, string>` index-signature trap).
 * The literal type is inferred from the `as const` map.
 */
export const STATUS_COLOR_FALLBACK = PALETTE_STATUS_MAP.muted;

/**
 * Resolve a status string to a CSS color expression. Lowercases the
 * input for case-insensitive matching; falls back to
 * {@link STATUS_COLOR_FALLBACK} when status is null, empty, or
 * unmapped. Always use this in lieu of inline `?? '#6f797d'`
 * defaults from housekeeping / reservation status maps.
 */
export function statusColor(status: string | null | undefined): string {
  if (!status) return STATUS_COLOR_FALLBACK;
  // Bracket access is typed via StatusKey (the literal-union narrowed
  // by `as const`), then cast back to string so the actual return
  // type is plain `string` for callers.
  return (PALETTE_STATUS_MAP as Record<StatusKey, string>)[
    status.toLowerCase() as StatusKey
  ] ?? STATUS_COLOR_FALLBACK;
}

// ────────────────────────────────────────────────────────────────────
// withAlpha — token-alpha variator
// ────────────────────────────────────────────────────────────────────

/**
 * Compose a `color-mix(in srgb, ${token} ${pct}%, transparent)`
 * expression so callers can vary the alpha of any design-token
 * color without introducing a new hex literal. The browser
 * resolves the inner var() at paint time, so light/dark switching
 * still works.
 *
 * Accepts either `'var(--success)'` (already wrapped) or `'--success'`
 * (alias) — both are normalised to the wrapped form.
 *
 * @example
 *   withAlpha('--accent', 18)
 *   // → 'color-mix(in srgb, var(--accent) 18%, transparent)'
 *
 *   withAlpha('var(--success)', 30)
 *   // → 'color-mix(in srgb, var(--success) 30%, transparent)'
 *
 * @param token Token alias (with or without `var(...)` wrapping).
 *              Type-checked against the canonical `--*` set in
 *              {@link SemanticToken}, but `string` fallback is
 *              accepted to ease integration with `getComputedStyle`
 *              lookups.
 * @param pct   Opacity percentage in 0-100. Out-of-range values
 *              are NOT clamped — pass what the caller intends.
 */
export function withAlpha(token: SemanticToken | string, pct: number): string {
  const tokenExpr = token.startsWith('var(') ? token : `var(${token})`;
  return `color-mix(in srgb, ${tokenExpr} ${pct}%, transparent)`;
}
