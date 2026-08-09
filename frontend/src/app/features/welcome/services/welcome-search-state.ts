/**
 * Persistencia del booking bar del welcome (destino, fechas, huéspedes).
 *
 * El booking bar guarda su último estado en localStorage al navegar a /search
 * y lo precarga cuando el usuario vuelve al welcome. Estas funciones puras
 * son la única pieza con lógica (validación de rangos, saneo de fechas
 * pasadas, tolerancia a JSON corrupto) y se testean de forma aislada.
 */

export const WELCOME_SEARCH_STORAGE_KEY = 'hoteldata.welcome_search_state';

export interface WelcomeSearchState {
  destination: string;
  checkIn: string;
  checkOut: string;
  adults: number;
  children: number;
  rooms: number;
}

const ADULTS_MIN = 1;
const ADULTS_MAX = 9;
const CHILDREN_MIN = 0;
const CHILDREN_MAX = 6;
const ROOMS_MIN = 1;
const ROOMS_MAX = 5;

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function clamp(value: unknown, min: number, max: number, fallback: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(Math.max(Math.round(n), min), max);
}

function sanitizeDate(value: unknown): string {
  if (typeof value !== 'string' || !ISO_DATE.test(value)) return '';
  // Rechaza fechas sintácticamente ISO pero imposibles (ej. 2026-13-45): el
  // round-trip por Date devuelve NaN o un mes distinto al declarado.
  const [y, m, d] = value.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  if (Number.isNaN(dt.getTime())) return '';
  if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) return '';
  return value;
}

/**
 * Guarda el estado del booking bar. Tolerante a localStorage no disponible
 * (private mode / quota): un fallo de escritura nunca rompe la navegación.
 */
export function saveWelcomeSearchState(state: WelcomeSearchState): void {
  try {
    localStorage.setItem(WELCOME_SEARCH_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // localStorage lanzado (quota, private mode) — la búsqueda sigue adelante.
  }
}

/**
 * Carga el último estado guardado, saneado contra la fecha de hoy.
 *
 * - Fechas pasadas (checkIn < today) se descartan por completo: no tiene
 *   sentido precargar un rango ya vencido.
 * - Solo el check-out pasado se limpia, manteniendo un check-in futuro.
 * - Números fuera de rango se clampan; JSON corrupto devuelve null.
 */
export function loadWelcomeSearchState(today: string): WelcomeSearchState | null {
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(WELCOME_SEARCH_STORAGE_KEY);
  } catch {
    return null;
  }
  if (!raw) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return null;
  }

  const p = parsed as Record<string, unknown>;
  const rawDestination = typeof p['destination'] === 'string' ? p['destination'] : '';
  const checkIn = sanitizeDate(p['checkIn']);
  const checkOut = sanitizeDate(p['checkOut']);
  const adults = clamp(p['adults'], ADULTS_MIN, ADULTS_MAX, 2);
  const children = clamp(p['children'], CHILDREN_MIN, CHILDREN_MAX, 0);
  const rooms = clamp(p['rooms'], ROOMS_MIN, ROOMS_MAX, 1);

  // Rango pasado (checkIn < today): descartar ambas fechas.
  if (checkIn && checkIn < today) {
    return { destination: rawDestination, checkIn: '', checkOut: '', adults, children, rooms };
  }

  return {
    destination: rawDestination,
    checkIn,
    checkOut: checkOut && checkOut < today ? '' : checkOut,
    adults,
    children,
    rooms,
  };
}
