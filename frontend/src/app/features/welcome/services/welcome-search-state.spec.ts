/**
 * Tests for the welcome booking-bar persistence helpers.
 *
 * The booking bar (destino, fechas, huéspedes) se guarda en localStorage al
 * navegar desde el welcome y se precarga al volver. Estos helpers son la
 * única pieza con lógica (validación, saneo de fechas pasadas, tolerancia a
 * datos corruptos) — por eso viven como funciones puras testeables.
 */
import {
  WELCOME_SEARCH_STORAGE_KEY,
  loadWelcomeSearchState,
  saveWelcomeSearchState,
} from './welcome-search-state';

const TODAY = '2026-08-08';

function stored(): Record<string, unknown> | null {
  const raw = localStorage.getItem(WELCOME_SEARCH_STORAGE_KEY);
  return raw ? JSON.parse(raw) : null;
}

describe('welcome-search-state', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('saveWelcomeSearchState', () => {
    it('serializes the full booking-bar state', () => {
      saveWelcomeSearchState({
        destination: 'Bolivia',
        checkIn: '2026-08-10',
        checkOut: '2026-08-15',
        adults: 3,
        children: 1,
        rooms: 2,
      });

      expect(stored()).toEqual({
        destination: 'Bolivia',
        checkIn: '2026-08-10',
        checkOut: '2026-08-15',
        adults: 3,
        children: 1,
        rooms: 2,
      });
    });

    it('persists an empty destination (only dates/guests) without throwing', () => {
      saveWelcomeSearchState({
        destination: '',
        checkIn: '2026-08-10',
        checkOut: '2026-08-15',
        adults: 2,
        children: 0,
        rooms: 1,
      });

      expect(stored()).not.toBeNull();
      expect(stored()!.destination).toBe('');
    });
  });

  describe('loadWelcomeSearchState', () => {
    it('restores a previously saved state', () => {
      saveWelcomeSearchState({
        destination: 'Hotel Lima Centro',
        checkIn: '2026-08-12',
        checkOut: '2026-08-18',
        adults: 4,
        children: 1,
        rooms: 1,
      });

      const state = loadWelcomeSearchState(TODAY);
      expect(state).toEqual({
        destination: 'Hotel Lima Centro',
        checkIn: '2026-08-12',
        checkOut: '2026-08-18',
        adults: 4,
        children: 1,
        rooms: 1,
      });
    });

    it('returns null when nothing is stored', () => {
      expect(loadWelcomeSearchState(TODAY)).toBeNull();
    });

    it('returns null on corrupt JSON (does not throw)', () => {
      localStorage.setItem(WELCOME_SEARCH_STORAGE_KEY, '{not valid json');
      expect(loadWelcomeSearchState(TODAY)).toBeNull();
    });

    it('returns null on a non-object payload', () => {
      localStorage.setItem(WELCOME_SEARCH_STORAGE_KEY, JSON.stringify(['nope']));
      expect(loadWelcomeSearchState(TODAY)).toBeNull();
    });

    it('drops stale check-in dates entirely (they are past)', () => {
      saveWelcomeSearchState({
        destination: 'Quito',
        checkIn: '2026-08-01', // pasado frente a TODAY
        checkOut: '2026-08-03',
        adults: 2,
        children: 0,
        rooms: 1,
      });

      const state = loadWelcomeSearchState(TODAY);
      expect(state).not.toBeNull();
      expect(state!.checkIn).toBe('');
      expect(state!.checkOut).toBe('');
      // El resto se conserva
      expect(state!.destination).toBe('Quito');
      expect(state!.adults).toBe(2);
    });

    it('drops stale check-out while keeping a future check-in', () => {
      saveWelcomeSearchState({
        destination: '',
        checkIn: '2026-08-10',
        checkOut: '2026-08-02', // pasado
        adults: 2,
        children: 0,
        rooms: 1,
      });

      const state = loadWelcomeSearchState(TODAY);
      expect(state!.checkIn).toBe('2026-08-10');
      expect(state!.checkOut).toBe('');
    });

    it('clamps guest counts to sane ranges', () => {
      saveWelcomeSearchState({
        destination: 'X',
        checkIn: '',
        checkOut: '',
        adults: 99,
        children: -3,
        rooms: 42,
      });

      const state = loadWelcomeSearchState(TODAY);
      expect(state!.adults).toBe(9);
      expect(state!.children).toBe(0);
      expect(state!.rooms).toBe(5);
    });

    it('ignores non-ISO date strings', () => {
      saveWelcomeSearchState({
        destination: 'X',
        checkIn: 'ayer',
        checkOut: '2026-08-15',
        adults: 2,
        children: 0,
        rooms: 1,
      });

      const state = loadWelcomeSearchState(TODAY);
      expect(state!.checkIn).toBe('');
      expect(state!.checkOut).toBe('2026-08-15');
    });

    it('keeps today as a valid check-in (not stale)', () => {
      saveWelcomeSearchState({
        destination: 'Hoy',
        checkIn: TODAY,
        checkOut: '2026-08-10',
        adults: 2,
        children: 0,
        rooms: 1,
      });

      const state = loadWelcomeSearchState(TODAY);
      expect(state!.checkIn).toBe(TODAY);
      expect(state!.checkOut).toBe('2026-08-10');
    });

    it('rejects impossible calendar dates like 2026-13-45', () => {
      saveWelcomeSearchState({
        destination: 'X',
        checkIn: '2026-13-45', // mes 13 / día 45 no existen
        checkOut: '2026-08-15',
        adults: 2,
        children: 0,
        rooms: 1,
      });

      const state = loadWelcomeSearchState(TODAY);
      expect(state!.checkIn).toBe('');
      expect(state!.checkOut).toBe('2026-08-15');
    });
  });
});
