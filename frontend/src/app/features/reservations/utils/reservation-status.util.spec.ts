import {
  BOOKING_CANCELLED,
  BOOKING_CHECKED_IN,
  BOOKING_CHECKED_OUT,
  BOOKING_CONFIRMED,
  BOOKING_PENDING,
  BOOKING_REJECTED,
  isBulkSelectable,
  STAY_CHECKED_IN,
  STAY_CHECKED_OUT,
  STAY_NO_SHOW,
  STAY_PENDING,
} from './reservation-status.util';

describe('isBulkSelectable — elegibilidad para acciones en lote (columna de selección)', () => {
  it('permite seleccionar pendientes (confirmación masiva)', () => {
    expect(isBulkSelectable(BOOKING_PENDING, STAY_PENDING)).toBe(true);
    // Legacy: reservas viejas sin stay_status.
    expect(isBulkSelectable(BOOKING_PENDING, '')).toBe(true);
    expect(isBulkSelectable(BOOKING_PENDING, null)).toBe(true);
  });

  it('permite seleccionar confirmadas (check-in masivo)', () => {
    expect(isBulkSelectable(BOOKING_CONFIRMED, STAY_PENDING)).toBe(true);
    expect(isBulkSelectable(BOOKING_CONFIRMED, '')).toBe(true);
  });

  it('excluye no-shows aunque el estado de reserva sea pendiente o confirmada', () => {
    expect(isBulkSelectable(BOOKING_PENDING, STAY_NO_SHOW)).toBe(false);
    expect(isBulkSelectable(BOOKING_CONFIRMED, STAY_NO_SHOW)).toBe(false);
  });

  it('excluye estados terminales del booking (rejected / cancelled)', () => {
    expect(isBulkSelectable(BOOKING_REJECTED, STAY_PENDING)).toBe(false);
    expect(isBulkSelectable(BOOKING_CANCELLED, STAY_PENDING)).toBe(false);
  });

  it('excluye fases operativas del stay sin acción en lote (checked_in / checked_out)', () => {
    expect(isBulkSelectable(BOOKING_CONFIRMED, STAY_CHECKED_IN)).toBe(false);
    expect(isBulkSelectable(BOOKING_CONFIRMED, STAY_CHECKED_OUT)).toBe(false);
    expect(isBulkSelectable(BOOKING_CHECKED_IN, STAY_CHECKED_IN)).toBe(false);
    expect(isBulkSelectable(BOOKING_CHECKED_OUT, STAY_CHECKED_OUT)).toBe(false);
  });

  it('excluye filas sin estado conocido', () => {
    expect(isBulkSelectable('', '')).toBe(false);
    expect(isBulkSelectable(null, null)).toBe(false);
    expect(isBulkSelectable('unknown_status', '')).toBe(false);
  });
});
