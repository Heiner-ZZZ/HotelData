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

describe('buildColumnDefs — columna de acciones (confirmar/rechazar)', () => {
  const callbacks = {
    onConfirm: jest.fn(),
    onReject: jest.fn(),
    isStaff: () => true,
  };

  function actionsCol() {
    return buildColumnDefs(callbacks).find((c) => !c.field && !c.headerName && c.sortable === false)!;
  }

  function renderActions(status: string, staff = true) {
    callbacks.isStaff = () => staff;
    const renderer = actionsCol().cellRenderer as (params: any) => HTMLElement;
    const out = renderer({ value: '', data: { status, bookingId: 'BK-1', guestName: 'Horuz' } });
    // El renderer devuelve '' (sin acciones) para filas no pendientes o no staff.
    if (!out) return document.createElement('div');
    return out;
  }

  it('da espacio suficiente a la columna para que los dos botones no se peguen', () => {
    expect(actionsCol().width).toBeGreaterThanOrEqual(88);
  });

  it('separa los dos botones con un gap de al menos 8px', () => {
    const wrap = renderActions('pending') as HTMLDivElement;
    const gap = Number.parseFloat(wrap.style.gap || '0');
    expect(gap).toBeGreaterThanOrEqual(8);
  });

  it('da un tamaño de toque cómodo a cada botón (≥ 2rem / 32px)', () => {
    const wrap = renderActions('pending') as HTMLDivElement;
    const buttons = [...wrap.querySelectorAll('button')];
    expect(buttons).toHaveLength(2);
    for (const btn of buttons) {
      // Los estilos inline usan rem; 2rem = 32px a font-size raíz 16px.
      const w = Number.parseFloat(btn.style.width || '0') * 16;
      const h = Number.parseFloat(btn.style.height || '0') * 16;
      expect(w).toBeGreaterThanOrEqual(32);
      expect(h).toBeGreaterThanOrEqual(32);
    }
  });

  it('da nombre accesible a cada botón de icono (aria-label, no solo title)', () => {
    const wrap = renderActions('pending') as HTMLDivElement;
    const buttons = [...wrap.querySelectorAll('button')];
    const confirm = buttons.find((b) => b.querySelector('.material-symbols-outlined')?.textContent === 'check_circle')!;
    const reject = buttons.find((b) => b.querySelector('.material-symbols-outlined')?.textContent === 'cancel')!;
    expect(confirm.getAttribute('aria-label')).toBe('Confirmar reserva');
    expect(reject.getAttribute('aria-label')).toBe('Rechazar reserva');
  });

  it('solo renderiza acciones para filas pendientes y staff', () => {
    expect((renderActions('pending') as HTMLDivElement).querySelectorAll('button')).toHaveLength(2);
    expect((renderActions('confirmed') as HTMLDivElement).querySelectorAll('button')).toHaveLength(0);
    expect((renderActions('pending', false) as HTMLDivElement).querySelectorAll('button')).toHaveLength(0);
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
