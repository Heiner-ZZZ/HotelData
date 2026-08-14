import { buildCalendarMonth, cellTooltip } from './availability.helpers';
import type { AvailabilityInventoryItem } from './models/availability.model';

function inv(overrides: Partial<AvailabilityInventoryItem>): AvailabilityInventoryItem {
  return {
    date: '2026-09-01',
    roomTypeId: 'RT-STD',
    roomTypeName: 'Habitación Standard',
    totalRooms: 10,
    availableRooms: 5,
    blockedRooms: 0,
    occupancyLabel: '5/10 disponibles',
    occupancyPct: 50,
    hasRate: true,
    ...overrides,
  };
}

describe('availability.helpers — cobertura de tarifas', () => {
  it('propaga hasRate del item de inventario a la celda del calendario', () => {
    const items = [
      inv({ date: '2026-09-01', hasRate: true }),
      inv({ date: '2026-09-02', hasRate: false }),
    ];
    const cal = buildCalendarMonth(2026, 8, items); // septiembre
    const byDate = new Map(cal.days.map((d) => [d.date, d]));
    const cell1 = byDate.get('2026-09-01')!.roomTypes[0];
    const cell2 = byDate.get('2026-09-02')!.roomTypes[0];
    expect(cell1.hasRate).toBe(true);
    expect(cell2.hasRate).toBe(false);
  });

  it('el tooltip avisa SIN TARIFA cuando hay disponibilidad pero no tarifa abierta', () => {
    const cell = inv({ date: '2026-09-02', hasRate: false, roomTypeName: 'Standard' });
    expect(cellTooltip(cell, '2026-09-02')).toContain('SIN TARIFA');
    expect(cellTooltip(cell, '2026-09-02')).toContain('no vendible');
  });

  it('el tooltip NO avisa cuando la fecha tiene tarifa', () => {
    const cell = inv({ date: '2026-09-01', hasRate: true, roomTypeName: 'Standard' });
    expect(cellTooltip(cell, '2026-09-01')).not.toContain('SIN TARIFA');
  });
});
