/**
 * Contract test for the semantic alias tokens the products feature relies on
 * (--surface-card, --text-primary, --accent-primary, --border-subtle, ...).
 *
 * These aliases are NOT canonical tokens; they are legacy feature names that
 * must be mapped to the v2 canonical tokens (--surface, --app-text, --accent,
 * ...) in BOTH theme blocks. If an alias is only defined in :root, the page
 * stays "light" inside a dark app shell — the exact bug this test guards.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const SCSS_PATH = resolve(__dirname, '../../../../src/styles/_scss-variables.scss');
const scss = readFileSync(SCSS_PATH, 'utf8');

function extractBlock(selector: string): string {
  const marker = `${selector} {`;
  const start = scss.indexOf(marker);
  if (start === -1) {
    throw new Error(`Theme block "${selector} {" not found in _scss-variables.scss`);
  }
  const open = scss.indexOf('{', start);
  let depth = 0;
  for (let i = open; i < scss.length; i++) {
    if (scss[i] === '{') depth++;
    else if (scss[i] === '}') {
      depth--;
      if (depth === 0) return scss.slice(open + 1, i);
    }
  }
  throw new Error(`Unterminated theme block for "${selector}"`);
}

/** Legacy alias names used across features (products, account, billing, ...). */
const ALIAS_TOKENS = [
  '--surface-card',
  '--surface-muted',
  '--surface-default',
  '--text-primary',
  '--text-secondary',
  '--text-muted',
  '--text-tertiary',
  '--accent-primary',
  '--text-on-accent',
  '--border-subtle',
  '--border-default',
  '--color-primary',
  '--color-on-primary',
  '--color-success',
  '--color-success-bg',
  '--color-success-text',
  '--color-warning',
  '--color-warning-bg',
  '--color-warning-text',
  '--color-warning-border',
  '--color-danger',
];

/** Canonical tokens the aliases resolve to; they must exist in :root. */
const CANONICAL_TOKENS = [
  '--surface',
  '--surface-hover',
  '--app-text',
  '--muted-text',
  '--accent',
  '--on-accent',
  '--app-border',
  '--gray-50',
  '--gray-100',
  '--gray-200',
  '--gray-400',
  '--gray-500',
  '--gray-600',
  '--success',
  '--success-light',
  '--success-strong',
  '--warning',
  '--warning-light',
  '--warning-strong',
  '--danger',
  '--danger-strong',
  '--indigo',
  '--indigo-strong',
];

describe('theme tokens contract (_scss-variables.scss)', () => {
  const light = extractBlock(':root');
  const dark = extractBlock('[data-theme="dark"]');

  describe('canonical tokens', () => {
    it.each(CANONICAL_TOKENS)('%s is defined in the light theme', (token) => {
      expect(light).toMatch(new RegExp(`${token}\\s*:`));
    });
  });

  describe('legacy alias tokens used by the products feature', () => {
    it.each(ALIAS_TOKENS)('%s is defined in the light theme', (token) => {
      expect(light).toMatch(new RegExp(`${token}\\s*:`));
    });

    it.each(ALIAS_TOKENS)('%s is defined in the dark theme', (token) => {
      expect(dark).toMatch(new RegExp(`${token}\\s*:`));
    });

    it.each(ALIAS_TOKENS)('%s aliases a canonical token (var() reference)', (token) => {
      expect(light).toMatch(new RegExp(`${token}\\s*:\\s*var\\(--`));
    });
  });
});
