import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';

import { ToastService } from '../../../../shared/services/toast.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { AuthService } from '../../../../core/auth/auth.service';
import type { OpenShiftOverview } from '../../services/shifts-api.service';
import { ShiftsApiService } from '../../services/shifts-api.service';
import { OpenShiftsOverviewPageComponent } from './open-shifts-overview-page';

const OPEN_SHIFTS: OpenShiftOverview[] = [
  {
    id: 'shift-1',
    prop_id: 1,
    hotel_name: 'Hotel Lima Centro',
    shift_type: 'morning',
    shift_label: 'Matutino (07:00-15:00)',
    employee: 'Carlos Pérez',
    opened_by: 'superadmin',
    start_time: new Date(Date.now() - 46 * 3600_000).toISOString(),
    cash_initial: 100,
    total_collected: 50,
    payment_breakdown: { cash: 30, card: 20, transfer: 0, other: 0, total: 50 },
    transaction_count: 3,
    hours_open: 46.2,
    max_open_hours: 12,
    is_expired: true,
    expires_at: new Date(Date.now() - 34 * 3600_000).toISOString(),
  },
  {
    id: 'shift-2',
    prop_id: 2,
    hotel_name: 'Resort Cancún Playa',
    shift_type: 'evening',
    shift_label: 'Nocturno (23:00-07:00)',
    employee: 'María Gómez',
    opened_by: 'gerente2',
    start_time: new Date(Date.now() - 3 * 3600_000).toISOString(),
    cash_initial: 50,
    total_collected: 10,
    transaction_count: 1,
    hours_open: 3.1,
    max_open_hours: 12,
    is_expired: false,
    expires_at: new Date(Date.now() + 9 * 3600_000).toISOString(),
  },
];

describe('OpenShiftsOverviewPageComponent', () => {
  function setup(opts: { canManage?: boolean; items?: OpenShiftOverview[] } = {}) {
    const items = opts.items ?? OPEN_SHIFTS;
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
    } as unknown as Router;
    const api = {
      getOpenShiftsOverview: jest.fn(() => of({ items, total: items.length })),
      closeShift: jest.fn(() => of({ shift: {}, message: 'Turno cerrado', summary: {} })),
    } as unknown as ShiftsApiService;
    const auth = {
      hasPermission: jest.fn((p: string) => (opts.canManage === false ? p !== 'shifts.manage' : true)),
    } as unknown as AuthService;
    const confirmDialog = {
      open: jest.fn(() => Promise.resolve(true)),
      openPrompt: jest.fn(() => Promise.resolve('Turno olvidado por gerencia')),
    } as unknown as ConfirmDialogService;

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [OpenShiftsOverviewPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: ShiftsApiService, useValue: api },
        { provide: AuthService, useValue: auth },
        { provide: ConfirmDialogService, useValue: confirmDialog },
      ],
    });

    const fixture = TestBed.createComponent(OpenShiftsOverviewPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, api, router, toast: TestBed.inject(ToastService), auth, confirmDialog };
  }

  /** Hotel names in DOM order (first row = first rendered); skips the icon text. */
  function rowHotels(fixture: { nativeElement: HTMLElement }): string[] {
    return Array.from(fixture.nativeElement.querySelectorAll('.oso-row')).map((r) => {
      const el = r.querySelector('.oso-hotel');
      const text = Array.from(el?.childNodes ?? [])
        .filter((n) => n.nodeType === Node.TEXT_NODE)
        .map((n) => n.textContent ?? '')
        .join('')
        .trim();
      return text;
    });
  }

  it('carga y lista los turnos abiertos de todos los hoteles', () => {
    const { fixture, component } = setup();

    expect(component.loading()).toBe(false);
    expect(component.items().length).toBe(2);
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Hotel Lima Centro');
    expect(text).toContain('Resort Cancún Playa');
    expect(text).toContain('Carlos Pérez');
  });

  it('ordena por tiempo restante ascendente por defecto (menos tiempo primero), aunque el API llegue desordenado', () => {
    // El API devuelve primero el que vence en ~9h y después el vencido hace ~34h;
    // la tabla debe mostrar el vencido (menos tiempo restante) primero.
    const { component, fixture } = setup({ items: [OPEN_SHIFTS[1], OPEN_SHIFTS[0]] });

    expect(component.sortedItems().map((r) => r.id)).toEqual(['shift-1', 'shift-2']);
    expect(rowHotels(fixture)[0]).toBe('Hotel Lima Centro');
    expect(rowHotels(fixture)[1]).toBe('Resort Cancún Playa');
  });

  it('alterna el orden con el control y refleja el cambio en la tabla', () => {
    const { component, fixture } = setup({ items: [OPEN_SHIFTS[1], OPEN_SHIFTS[0]] });

    expect(component.sortOrder()).toBe('asc');
    // El control existe y muestra el modo actual.
    const headerText = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(headerText).toContain('Más urgentes primero');

    component.toggleSortOrder();
    fixture.detectChanges();

    expect(component.sortOrder()).toBe('desc');
    expect(component.sortedItems().map((r) => r.id)).toEqual(['shift-2', 'shift-1']);
    expect(rowHotels(fixture)[0]).toBe('Resort Cancún Playa');
    expect(rowHotels(fixture)[1]).toBe('Hotel Lima Centro');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Menos urgentes primero');
  });

  it('la cabecera de la columna Tiempo restante también alterna el orden', () => {
    const { component, fixture } = setup();

    const th = Array.from(fixture.nativeElement.querySelectorAll('th'))
      .find((el) => (el.textContent ?? '').includes('Tiempo restante')) as HTMLElement | undefined;
    expect(th).toBeDefined();

    th?.click();
    fixture.detectChanges();

    expect(component.sortOrder()).toBe('desc');
  });

  it('los turnos sin estimación de vencimiento quedan al final en ambos órdenes', () => {
    const withoutExpiry: OpenShiftOverview = {
      ...OPEN_SHIFTS[1],
      id: 'shift-3',
      hotel_name: 'Hotel Sin Expiry',
      expires_at: null as unknown as string,
    };
    const { component } = setup({ items: [withoutExpiry, OPEN_SHIFTS[0], OPEN_SHIFTS[1]] });

    expect(component.sortedItems().map((r) => r.id)).toEqual(['shift-1', 'shift-2', 'shift-3']);
    component.toggleSortOrder();
    expect(component.sortedItems().map((r) => r.id)).toEqual(['shift-2', 'shift-1', 'shift-3']);
  });

  it('marca los turnos vencidos con el badge de estado', () => {
    const { fixture } = setup();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('VENCIDO');
    const badge = Array.from(fixture.nativeElement.querySelectorAll('.oso-state-badge')) as HTMLElement[];
    const expiredBadges = badge.filter(b => b.textContent?.includes('VENCIDO'));
    expect(expiredBadges.length).toBe(1);
    expect(expiredBadges[0].classList.contains('expired')).toBe(true);
  });

  it('formatea la antigüedad en horas y minutos', () => {
    const { component } = setup();

    expect(component.formatAge(46.2)).toBe('46h 12m');
    expect(component.formatAge(3.1)).toBe('3h 6m');
    expect(component.formatAge(0)).toBe('0m');
  });

  it('clasifica el estado por vencimiento y proximidad al límite', () => {
    const { component } = setup();

    expect(component.ageClass(OPEN_SHIFTS[0])).toBe('expired');
    expect(component.ageClass(OPEN_SHIFTS[1])).toBe('normal');

    // Cerca del límite (>= 75% del max) → warning
    const near = { ...OPEN_SHIFTS[1], hours_open: 10, max_open_hours: 12, is_expired: false };
    expect(component.ageClass(near)).toBe('warning');
  });

  it('navega al dashboard del hotel al pulsar ir al turno', () => {
    const { component, router } = setup();

    component.goToShift(OPEN_SHIFTS[0]);

    expect(router.navigate).toHaveBeenCalledWith(['/management/shifts/dashboard'], {
      queryParams: { prop_id: 1, prop_label: 'Hotel Lima Centro' },
    });
  });

  it('muestra el estado vacío cuando no hay turnos abiertos', () => {
    const api = {
      getOpenShiftsOverview: jest.fn(() => of({ items: [], total: 0 })),
    } as unknown as ShiftsApiService;
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
    } as unknown as Router;

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [OpenShiftsOverviewPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: ShiftsApiService, useValue: api },
      ],
    });

    const fixture = TestBed.createComponent(OpenShiftsOverviewPageComponent);
    fixture.detectChanges();

    expect((fixture.nativeElement.textContent as string)).toContain('No hay turnos abiertos');
  });

  it('muestra el tiempo restante (countdown) hasta el vencimiento', () => {
    const { fixture, component } = setup();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Tiempo restante');
    // shift-2 vence en ~9h → "8h 59m restantes"
    expect(text).toContain('restantes');
    expect(component.countdownText(OPEN_SHIFTS[1])).toContain('restantes');
  });

  it('muestra "hace" para turnos ya vencidos', () => {
    const { fixture, component } = setup();

    // shift-1 venció hace ~34h → "hace 34h 0m"
    expect(component.countdownText(OPEN_SHIFTS[0])).toContain('hace');
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('hace');
  });

  it('muestra cuánto lleva acumulado en caja cada turno', () => {
    const { fixture } = setup();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('En caja');
    expect(text).toContain('$50.00');
    expect(text).toContain('$10.00');
  });

  it('suma el efectivo retenido en los turnos vencidos (KPI)', () => {
    const { component, fixture } = setup();

    // shift-1 vencido: 100 (fondo) + 50 (cobrado) = 150
    expect(component.retainedExpired()).toBe(150);
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Retenido en vencidos');
    expect(text).toContain('$150.00');
  });

  it('no muestra el botón de cierre forzado sin permiso shifts.manage', () => {
    const { component, fixture } = setup({ canManage: false });

    expect(component.canForceClose()).toBe(false);
    const buttons = Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLElement[];
    expect(buttons.some(b => b.textContent?.includes('Cierre forzado'))).toBe(false);
  });

  it('cierra forzosamente con doble confirmación y motivo, y recarga', async () => {
    const { component, api, confirmDialog, toast, fixture } = setup();

    await component.forceClose(OPEN_SHIFTS[0]);

    expect(confirmDialog.open).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Cerrar forzosamente el turno',
      variant: 'danger',
      mode: 'delete',
      modeDetail: expect.stringContaining('Hotel Lima Centro'),
    }));
    expect(confirmDialog.openPrompt).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Confirmar cierre forzado',
      variant: 'danger',
      mode: 'delete',
      input: expect.objectContaining({ label: expect.stringContaining('Motivo') }),
    }));
    expect(api.closeShift).toHaveBeenCalledWith(
      'shift-1',
      150, // cash_counted = fondo + cobrado (arqueo simplificado)
      undefined,
      undefined,
      undefined,
      undefined,
      true,
      'Turno olvidado por gerencia',
    );
    expect(toast.toasts().some((t) => t.message.includes('cerrado forzosamente') && t.type === 'success')).toBe(true);
    // recarga tras el cierre
    expect(api.getOpenShiftsOverview).toHaveBeenCalledTimes(2);
  });

  it('muestra en el 2do diálogo el desglose del arqueo esperado (fondo + cobrado por método) antes de confirmar', async () => {
    const { component, confirmDialog } = setup();

    await component.forceClose(OPEN_SHIFTS[0]);

    const promptCfg = (confirmDialog.openPrompt as jest.Mock).mock.calls[0][0];
    expect(promptCfg.details).toBeDefined();
    const joined = (promptCfg.details as string[]).join('\n');
    expect(joined).toContain('Fondo inicial');
    expect(joined).toContain('$100.00');
    expect(joined).toContain('Efectivo');
    expect(joined).toContain('$30.00');
    expect(joined).toContain('Tarjeta');
    expect(joined).toContain('$20.00');
    expect(joined).toContain('Total esperado');
    expect(joined).toContain('$150.00');
  });

  it('omite del resumen los métodos con $0', async () => {
    const { component, confirmDialog } = setup();

    await component.forceClose({ ...OPEN_SHIFTS[0], payment_breakdown: { cash: 50, card: 0, transfer: 0, other: 0, total: 50 } });

    const promptCfg = (confirmDialog.openPrompt as jest.Mock).mock.calls[0][0];
    const joined = (promptCfg.details as string[]).join('\n');
    expect(joined).not.toContain('Tarjeta');
    expect(joined).not.toContain('Transferencias');
  });

  it('no llama al API si cancela la primera confirmación', async () => {
    const { component, api, confirmDialog } = setup();
    (confirmDialog.open as jest.Mock).mockResolvedValue(false);

    await component.forceClose(OPEN_SHIFTS[0]);

    expect(confirmDialog.openPrompt).not.toHaveBeenCalled();
    expect(api.closeShift).not.toHaveBeenCalled();
  });

  it('no llama al API si cancela la segunda confirmación (motivo)', async () => {
    const { component, api, confirmDialog } = setup();
    (confirmDialog.openPrompt as jest.Mock).mockResolvedValue(null);

    await component.forceClose(OPEN_SHIFTS[0]);

    expect(api.closeShift).not.toHaveBeenCalled();
  });

  it('se auto-refresca cada 30 minutos', () => {
    jest.useFakeTimers();
    const api = {
      getOpenShiftsOverview: jest.fn(() => of({ items: OPEN_SHIFTS, total: 2 })),
    } as unknown as ShiftsApiService;
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
    } as unknown as Router;

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [OpenShiftsOverviewPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: ShiftsApiService, useValue: api },
      ],
    });

    const fixture = TestBed.createComponent(OpenShiftsOverviewPageComponent);
    fixture.detectChanges();
    expect(api.getOpenShiftsOverview).toHaveBeenCalledTimes(1);

    jest.advanceTimersByTime(30 * 60 * 1000);
    expect(api.getOpenShiftsOverview).toHaveBeenCalledTimes(2);

    jest.useRealTimers();
  });

  it('muestra un toast cuando la carga falla', () => {
    const api = {
      getOpenShiftsOverview: jest.fn(() => throwError(() => ({ status: 500 }))),
    } as unknown as ShiftsApiService;
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
    } as unknown as Router;

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [OpenShiftsOverviewPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: ShiftsApiService, useValue: api },
      ],
    });

    // The constructor fires load() synchronously, so the spy must exist first.
    const toast = TestBed.inject(ToastService);
    const toastSpy = jest.spyOn(toast, 'error').mockImplementation(() => undefined);
    const fixture = TestBed.createComponent(OpenShiftsOverviewPageComponent);
    fixture.detectChanges();

    expect(toastSpy).toHaveBeenCalled();
    expect(fixture.componentInstance.loading()).toBe(false);
  });
});
