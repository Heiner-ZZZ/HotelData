import type { ColDef } from 'ag-grid-community';

import { buildColumnDefs } from './reservations-list-page.columns';

function stayStatusCol(): ColDef {
  const defs = buildColumnDefs({
    onConfirm: jest.fn(),
    onReject: jest.fn(),
    isStaff: () => true,
  });
  return defs.find((c) => c.field === 'stayStatus')!;
}

function renderCell(row: { stayStatus?: string; reopenWindow?: string | null; noShowReopenedAt?: string | null }) {
  const renderer = stayStatusCol().cellRenderer as (params: any) => HTMLElement;
  return renderer({ value: row.stayStatus ?? '', data: row });
}

describe('buildColumnDefs — marcador de no-show en la lista', () => {
  it('marca el no-show reabrible con el chip Reabrible y title de ventana abierta', () => {
    const el = renderCell({ stayStatus: 'no_show', reopenWindow: 'open' });
    expect(el.textContent).toContain('No-show');
    expect(el.textContent).toContain('Reabrible');
    expect(el.title).toContain('reabrible');
  });

  it('no muestra el chip en no-shows con ventana cerrada (too_late / stay_ended)', () => {
    for (const window of ['too_late', 'stay_ended']) {
      const el = renderCell({ stayStatus: 'no_show', reopenWindow: window });
      expect(el.textContent).toContain('No-show');
      expect(el.textContent).not.toContain('Reabrible');
      // too_late → 'cerrada'; stay_ended → 'cerró'.
      expect(el.title).toMatch(/cerrad|cerró/);
    }
  });

  it('muestra el marcador básico cuando la ventana es desconocida (backend viejo)', () => {
    const el = renderCell({ stayStatus: 'no_show', reopenWindow: null });
    expect(el.textContent).toContain('No-show');
    expect(el.textContent).not.toContain('Reabrible');
  });

  it('no agrega el marcador a reservas que no son no-show', () => {
    for (const stayStatus of ['checked_in', 'checked_out', 'pending', '']) {
      const el = renderCell({ stayStatus, reopenWindow: null });
      expect(el.textContent).not.toContain('No-show');
    }
  });
});

describe('buildColumnDefs — marcador de reapertura (huésped llegó tras el no-show)', () => {
  it('marca con chip Reabierta una reserva reabierta pendiente dentro de la ventana', () => {
    const el = renderCell({ stayStatus: 'pending', reopenWindow: 'open', noShowReopenedAt: '2026-08-15T14:56:25.121000' });
    expect(el.textContent).toContain('Pendiente');
    expect(el.textContent).toContain('Reabierta');
    expect(el.title).toContain('Reabierta tras no-show');
  });

  it('marca también la reabierta ya chequeada dentro de la ventana', () => {
    const el = renderCell({ stayStatus: 'checked_in', reopenWindow: 'open', noShowReopenedAt: '2026-08-15T14:56:25.121000' });
    expect(el.textContent).toContain('Check-in');
    expect(el.textContent).toContain('Reabierta');
    expect(el.title).toContain('Reabierta tras no-show');
  });

  it('no muestra el chip fuera de la ventana o sin marca de reapertura', () => {
    for (const reopenWindow of ['too_late', 'stay_ended', null]) {
      const el = renderCell({ stayStatus: 'pending', reopenWindow, noShowReopenedAt: '2026-08-15T14:56:25.121000' });
      expect(el.textContent).not.toContain('Reabierta');
    }
    const plain = renderCell({ stayStatus: 'pending', reopenWindow: 'open', noShowReopenedAt: null });
    expect(plain.textContent).not.toContain('Reabierta');
    expect(plain.textContent).toContain('Pendiente');
  });

  it('no mezcla el marcador de reapertura con el de no-show activo', () => {
    const el = renderCell({ stayStatus: 'no_show', reopenWindow: 'open', noShowReopenedAt: '2026-08-15T14:56:25.121000' });
    expect(el.textContent).toContain('No-show');
    expect(el.textContent).not.toContain('Reabierta');
  });
});
