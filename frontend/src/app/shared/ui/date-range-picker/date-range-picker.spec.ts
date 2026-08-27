import { TestBed } from '@angular/core/testing';

import { DateRangePickerComponent } from './date-range-picker';

/**
 * El date-range-picker es el calendario compartido de /search, /welcome y
 * /account/bookings/new (rn-planner-section). Soportar DOS gestos de rango:
 *
 *  1. ARRASTRE (regresión): mousedown en un día, arrastrar y soltar en otro.
 *     Si se arrastra hacia atrás, la validación actual intercambia
 *     (el más temprano = entrada, el más tardío = salida).
 *  2. CLIC-CLIC (nuevo): clic en un día (entrada) y clic en otro (salida),
 *     con la MISMA validación de orden: si el segundo cae antes del primero,
 *     se posicionan correctamente como entrada/salida (swap).
 */
describe('DateRangePickerComponent — selección por clic-clic y arrastre', () => {
  function setup(initial: { minDate?: string; startDate?: string; endDate?: string } = {}) {
    TestBed.configureTestingModule({
      imports: [DateRangePickerComponent],
    });
    const fixture = TestBed.createComponent(DateRangePickerComponent);
    const comp = fixture.componentInstance;
    fixture.componentRef.setInput('minDate', initial.minDate ?? '');
    fixture.componentRef.setInput('startDate', initial.startDate ?? '');
    fixture.componentRef.setInput('endDate', initial.endDate ?? '');
    fixture.detectChanges();
    comp.open(); // el grid vive dentro del popover (@if isOpen())
    fixture.detectChanges();
    return { fixture, comp };
  }

  /** Busca el botón del día en el mes actual (ignora días de otros meses). */
  function dayButton(fixture: ReturnType<typeof setup>['fixture'], year: number, month: number, day: number): HTMLButtonElement {
    const comp = fixture.componentInstance as DateRangePickerComponent;
    comp.currentYear.set(year);
    comp.currentMonth.set(month);
    fixture.detectChanges();
    const buttons = Array.from(fixture.nativeElement.querySelectorAll('button.dp-day')) as HTMLButtonElement[];
    const found = buttons.find((b) => !b.classList.contains('dp-other-month') && b.textContent?.trim() === String(day));
    if (!found) throw new Error(`No se encontró el día ${year}-${month + 1}-${day} en el grid`);
    return found;
  }

  /** Simula un clic de ratón: mousedown + mouseup en la misma celda. */
  function clickDay(fixture: ReturnType<typeof setup>['fixture'], year: number, month: number, day: number): void {
    const btn = dayButton(fixture, year, month, day);
    btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
  }

  /** Simula un arrastre: mousedown en un día, mouseenter en otro, mouseup ahí. */
  function dragDays(
    fixture: ReturnType<typeof setup>['fixture'],
    from: [number, number, number],
    to: [number, number, number],
  ): void {
    const [fy, fm, fd] = from;
    const [ty, tm, td] = to;
    const startBtn = dayButton(fixture, fy, fm, fd);
    startBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    const hoverBtn = dayButton(fixture, ty, tm, td);
    hoverBtn.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    hoverBtn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
  }

  /** Simula el padre controlado: cada emisión actualiza los inputs. */
  function wireControlledParent(comp: DateRangePickerComponent, fixture: ReturnType<typeof setup>['fixture']) {
    const emitted = { start: [] as string[], end: [] as string[] };
    comp.startChange.subscribe((v) => {
      emitted.start.push(v);
      fixture.componentRef.setInput('startDate', v);
      fixture.detectChanges();
    });
    comp.endChange.subscribe((v) => {
      emitted.end.push(v);
      fixture.componentRef.setInput('endDate', v);
      fixture.detectChanges();
    });
    return emitted;
  }

  const SEP = { year: 2026, month: 8 }; // Septiembre 2026 (mes 0-indexed)

  // ── CLIC-CLIC ───────────────────────────────────────────────────────────

  it('el primer clic fija la ENTRADA y queda a la espera de la salida (no crea misma fecha)', () => {
    const { fixture, comp } = setup();
    const emitted = wireControlledParent(comp, fixture);

    clickDay(fixture, SEP.year, SEP.month, 5);

    expect(emitted.start).toEqual(['2026-09-05']);
    expect(emitted.end).toEqual(['']); // sin segunda fecha — no misma-fecha
    expect(comp.selectingEnd()).toBe(true);
  });

  it('el segundo clic POSTERIOR completa entrada → salida y resalta el rango', () => {
    const { fixture, comp } = setup();
    const emitted = wireControlledParent(comp, fixture);

    clickDay(fixture, SEP.year, SEP.month, 5); // 1er clic: entrada
    expect(emitted.start).toEqual(['2026-09-05']);
    expect(comp.selectingEnd()).toBe(true);

    clickDay(fixture, SEP.year, SEP.month, 8); // 2º clic: salida

    expect(emitted.start.at(-1)).toBe('2026-09-05'); // restaura la entrada
    expect(emitted.end).toEqual(['', '', '2026-09-08']);
    expect(comp.selectingEnd()).toBe(false);
    expect(comp.startDate()).toBe('2026-09-05');
    expect(comp.endDate()).toBe('2026-09-08');

    // El rango se resalta: entrada, salida y días intermedios.
    expect(dayButton(fixture, SEP.year, SEP.month, 5).classList.contains('dp-start')).toBe(true);
    expect(dayButton(fixture, SEP.year, SEP.month, 8).classList.contains('dp-end')).toBe(true);
    expect(dayButton(fixture, SEP.year, SEP.month, 6).classList.contains('dp-range')).toBe(true);
  });

  it('el segundo clic ANTERIOR intercambia: el más temprano pasa a ser la entrada', () => {
    const { fixture, comp } = setup();
    const emitted = wireControlledParent(comp, fixture);

    clickDay(fixture, SEP.year, SEP.month, 8); // 1er clic: entrada 08
    clickDay(fixture, SEP.year, SEP.month, 5); // 2º clic ANTES de la entrada

    expect(emitted.start.at(-1)).toBe('2026-09-05'); // clic temprano = entrada
    expect(emitted.end).toEqual(['', '', '2026-09-08']); // entrada previa = salida
    expect(comp.selectingEnd()).toBe(false);
    expect(comp.startDate()).toBe('2026-09-05');
    expect(comp.endDate()).toBe('2026-09-08');
  });

  it('doble clic en el mismo día = misma fecha de entrada y salida', () => {
    const { fixture, comp } = setup();
    const emitted = wireControlledParent(comp, fixture);

    clickDay(fixture, SEP.year, SEP.month, 5);
    clickDay(fixture, SEP.year, SEP.month, 5);

    expect(emitted.start.at(-1)).toBe('2026-09-05');
    expect(emitted.end).toEqual(['', '', '2026-09-05']);
    expect(comp.selectingEnd()).toBe(false);
  });

  it('tras un rango completo, un clic inicia una selección NUEVA (no mueve la salida)', () => {
    const { fixture, comp } = setup();
    const emitted = wireControlledParent(comp, fixture);

    clickDay(fixture, SEP.year, SEP.month, 5);
    clickDay(fixture, SEP.year, SEP.month, 8); // rango completo 05 → 08
    expect(comp.selectingEnd()).toBe(false);

    clickDay(fixture, SEP.year, SEP.month, 12); // reinicia la selección

    expect(emitted.start.at(-1)).toBe('2026-09-12');
    expect(emitted.end.at(-1)).toBe('');
    expect(comp.selectingEnd()).toBe(true);
  });

  it('los días deshabilitados no responden al clic', () => {
    const { fixture, comp } = setup({ minDate: '2026-09-10' });
    const emitted = wireControlledParent(comp, fixture);

    clickDay(fixture, SEP.year, SEP.month, 5);

    expect(emitted.start).toEqual([]);
    expect(emitted.end).toEqual([]);
    expect(comp.selectingEnd()).toBe(false);
  });

  it('la activación por TECLADO (Enter/Espacio, click detail 0) usa el mismo flujo clic-clic', () => {
    const { fixture, comp } = setup();
    const emitted = wireControlledParent(comp, fixture);

    dayButton(fixture, SEP.year, SEP.month, 5).dispatchEvent(new MouseEvent('click', { bubbles: true, detail: 0 }));
    expect(emitted.start).toEqual(['2026-09-05']);
    expect(comp.selectingEnd()).toBe(true);

    dayButton(fixture, SEP.year, SEP.month, 8).dispatchEvent(new MouseEvent('click', { bubbles: true, detail: 0 }));
    expect(emitted.start).toEqual(['2026-09-05']);
    expect(emitted.end).toEqual(['', '2026-09-08']);
    expect(comp.selectingEnd()).toBe(false);
  });

  // ── ARRASTRE (regresión — comportamiento existente intacto) ─────────────

  it('REGRESIÓN: arrastrar hacia adelante selecciona entrada → salida', () => {
    const { fixture, comp } = setup();
    const emitted = wireControlledParent(comp, fixture);

    dragDays(fixture, [SEP.year, SEP.month, 5], [SEP.year, SEP.month, 8]);

    expect(emitted.start.at(-1)).toBe('2026-09-05');
    expect(emitted.end.at(-1)).toBe('2026-09-08');
    expect(comp.selectingEnd()).toBe(false);
  });

  it('REGRESIÓN: arrastrar hacia atrás intercambia (validación actual preservada)', () => {
    const { fixture, comp } = setup();
    const emitted = wireControlledParent(comp, fixture);

    dragDays(fixture, [SEP.year, SEP.month, 8], [SEP.year, SEP.month, 5]);

    expect(emitted.start.at(-1)).toBe('2026-09-05');
    expect(emitted.end.at(-1)).toBe('2026-09-08');
    expect(comp.selectingEnd()).toBe(false);
  });

  it('REGRESIÓN: un clic de ratón (detail 1) NO dispara el handler de teclado dos veces', () => {
    const { fixture, comp } = setup();
    const emitted = wireControlledParent(comp, fixture);

    // Un clic real de ratón dispara mousedown+mouseup Y click (detail >= 1).
    // El click con detail 1 debe ignorarse: el flujo lo resuelve mousedown/mouseup.
    const btn = dayButton(fixture, SEP.year, SEP.month, 5);
    btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, detail: 1 }));

    expect(emitted.start).toEqual(['2026-09-05']);
    expect(emitted.end).toEqual(['']);
  });
});
