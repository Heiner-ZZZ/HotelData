/**
 * Centralized reservation status utilities.
 *
 * Mirrors the backend StateMachine definitions in
 * `server/src/app/core/state_machine.py` so the frontend never
 * hard-codes status strings in templates or components.
 *
 * ── Booking status (booking.status) ──
 *   pending → confirmed → checked_in → checked_out
 *         ↘ rejected (terminal)
 *   Any → cancelled (terminal)
 *
 * ── Stay status (booking.stay_status) ──
 *   pending → checked_in → checked_out
 *         ↘ no_show (terminal)
 */

// ── Booking status helpers ────────────────────────────────────────────

export type BookingStatus = 'pending' | 'confirmed' | 'rejected' | 'checked_in' | 'checked_out' | 'cancelled';

export type StayStatus = 'pending' | 'checked_in' | 'checked_out' | 'no_show';

// ── Stay-status named constants (so we never hardcode strings) ────────

export const STAY_PENDING = 'pending' as const;
export const STAY_CHECKED_IN = 'checked_in' as const;
export const STAY_CHECKED_OUT = 'checked_out' as const;
export const STAY_NO_SHOW = 'no_show' as const;
export const STAY_CANCELLED = 'cancelled' as const;

// ── Booking-status named constants ────────────────────────────────────

export const BOOKING_PENDING = 'pending' as const;
export const BOOKING_CONFIRMED = 'confirmed' as const;
export const BOOKING_REJECTED = 'rejected' as const;
export const BOOKING_CHECKED_IN = 'checked_in' as const;
export const BOOKING_CHECKED_OUT = 'checked_out' as const;
export const BOOKING_CANCELLED = 'cancelled' as const;

export const BOOKING_STATUS_LABELS: Record<string, string> = {
  pending: 'Pendiente',
  confirmed: 'Confirmada',
  rejected: 'Rechazada',
  checked_in: 'Check-in Realizado',
  checked_out: 'Check-out Realizado',
  cancelled: 'Cancelada',
};

/**
 * Status colors — design-token backed (see
 * `frontend/src/styles/_scss-variables.scss`). Status keys kept
 * verbatim so the existing template lookups
 * (`[ngClass]="bookingStatusCss(status)"` etc.) keep working;
 * only the value shifts from a hardcoded hex to a `var(--token)`
 * reference. Auto-adapts to light/dark theme via the cascade.
 */
export const BOOKING_STATUS_COLORS: Record<string, string> = {
  pending: 'var(--cyan)',
  confirmed: 'var(--accent)',
  rejected: 'var(--danger)',
  checked_in: 'var(--success)',
  checked_out: 'var(--purple-strong)',
  cancelled: 'var(--muted-text)',
};

export const BOOKING_STATUS_ICONS: Record<string, string> = {
  pending: 'pending',
  confirmed: 'check_circle',
  rejected: 'cancel',
  checked_in: 'meeting_room',
  checked_out: 'logout',
  cancelled: 'block',
};

export const STAY_STATUS_LABELS: Record<string, string> = {
  pending: 'Sin Registrar',
  checked_in: 'Check-in Realizado',
  checked_out: 'Check-out Realizado',
  no_show: 'No Show',
};

// ── CSS class helpers ─────────────────────────────────────────────────

export const BOOKING_STATUS_CSS: Record<string, string> = {
  pending: 'hero-status-pending',
  confirmed: 'hero-status-confirmed',
  rejected: 'hero-status-rejected',
  checked_in: 'hero-status-checked-in',
  checked_out: 'hero-status-checked-out',
  cancelled: 'hero-status-cancelled',
};

// ── State machine transitions ─────────────────────────────────────────

const BOOKING_TRANSITIONS: Record<string, BookingStatus[]> = {
  pending: ['confirmed', 'rejected', 'cancelled'],
  confirmed: ['checked_in', 'cancelled'],
  rejected: [],
  checked_in: ['checked_out'],
  checked_out: [],
  cancelled: [],
};

const STAY_TRANSITIONS: Record<string, StayStatus[]> = {
  pending: ['checked_in', 'no_show'],
  checked_in: ['checked_out'],
  checked_out: [],
  no_show: [],
};

// ── Helper functions ──────────────────────────────────────────────────

export function getBookingStatusLabel(status: string | undefined | null): string {
  return BOOKING_STATUS_LABELS[status ?? ''] ?? status ?? 'Pendiente';
}

export function getBookingStatusColor(status: string | undefined | null): string {
  return BOOKING_STATUS_COLORS[status ?? ''] ?? 'var(--muted-text)';
}

export function getBookingStatusIcon(status: string | undefined | null): string {
  return BOOKING_STATUS_ICONS[status ?? ''] ?? 'help';
}

export function getBookingStatusCss(status: string | undefined | null): string {
  return BOOKING_STATUS_CSS[status ?? ''] ?? '';
}

export function getStayStatusLabel(status: string | undefined | null): string {
  return STAY_STATUS_LABELS[status ?? ''] ?? status ?? 'Sin Registrar';
}

/**
 * Determine the effective stay status to display/use.
 *
 * Business rule:
 * - If `stayStatus` is explicitly set (e.g. "checked_in", "checked_out"),
 *   use it — it takes priority because it reflects the current operational
 *   phase of the stay.
 * - Otherwise fall back to `status` for backward compatibility with older
 *   bookings that only have the reservation `status` field.
 *
 * This is the ONLY place this fallback logic should exist.
 */
export function effectiveStayStatus(
  stayStatus: string | undefined | null,
  status: string | undefined | null,
): string {
  return stayStatus || status || 'pending';
}

// ── Is the booking in a state where Mi Estancia is available? ─────────

export function canShowMiEstancia(
  stayStatus: string | undefined | null,
  status: string | undefined | null,
): boolean {
  return effectiveStayStatus(stayStatus, status) === 'checked_in';
}

// ── Is the reservation in an active (non-terminal) state? ────────────

export function isBookingActive(status: string | undefined | null): boolean {
  return status === 'pending' || status === 'confirmed' || status === 'checked_in';
}

// ── Can the booking be edited? ────────────────────────────────────────

export function canEditBooking(
  status: string | undefined | null,
  stayStatus: string | undefined | null,
  todayStr: string,
  checkOutDate: string | undefined | null,
): boolean {
  if (!status || !checkOutDate) return false;
  if (['cancelled', 'rejected', 'checked_out'].includes(status)) return false;
  const effectiveStay = effectiveStayStatus(stayStatus, status);
  if (effectiveStay === 'checked_out') return false;
  return todayStr < checkOutDate;
}

// ── Can staff assign rooms? ───────────────────────────────────────────

export function canAssignRooms(status: string | undefined | null): boolean {
  return status === BOOKING_CONFIRMED || status === BOOKING_CHECKED_IN;
}

// ── Quick status checks ──────────────────────────────────────────────

export function isPending(status: string | undefined | null): boolean {
  return status === BOOKING_PENDING;
}

export function isConfirmed(status: string | undefined | null): boolean {
  return status === BOOKING_CONFIRMED;
}

export function isCancelled(status: string | undefined | null): boolean {
  return status === BOOKING_CANCELLED || status === STAY_CANCELLED;
}

export function isCheckedIn(stayStatus: string | undefined | null): boolean {
  return stayStatus === STAY_CHECKED_IN;
}

export function isCheckedOut(stayStatus: string | undefined | null): boolean {
  return stayStatus === STAY_CHECKED_OUT;
}

/**
 * Return the row-level CSS class for a booking list item.
 * Used by reservations-list-page to highlight pending rows.
 */
export function getListRowCss(status: string | undefined | null): string | null {
  if (status === BOOKING_PENDING) return 'is-pending';
  return null;
}
