import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { AuthService } from '../../../../core/auth/auth.service';
import type { ShiftConfig } from '../../services/shifts-api.service';
import { ShiftsApiService } from '../../services/shifts-api.service';
import { ControlTurnosCajaPageComponent } from './control-turnos-caja-page';

const CUSTOM_CONFIG: ShiftConfig = {
  prop_id: 1,
  windows: {
    morning: { start: '10:00', end: '18:00' },
    afternoon: { start: '18:00', end: '02:00' },
    evening: { start: '02:00', end: '10:00' },
  },
  labels: {
    morning: 'Matutino (10:00-18:00)',
    afternoon: 'Vespertino (18:00-02:00)',
    evening: 'Nocturno (02:00-10:00)',
  },
  is_custom: true,
  max_open_hours: 6,
  notify_manager_hours: 5,
  updated_at: '2026-08-09T19:06:35.565000',
  updated_by: 'gerente_test',
};

describe('ControlTurnosCajaPageComponent', () => {
  function setup(
    opts: {
      canManage?: boolean;
      expired?: boolean;
      openedBy?: string;
      openedAt?: string;
      /** Overrides del shift activo (ej. payment_breakdown / stamped_payments_count). */
      shift?: Record<string, unknown>;
    } = {},
    apiOverrides: Partial<Record<'getShiftConfig', jest.Mock>> = {},
  ) {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
    } as unknown as Router;
    const propertyContext = {
      ready: signal(false),
      singleHotelMode: signal(false),
      currentPropId: signal(1),
      currentCurrency: signal('USD'),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;
    const api = {
      getActiveShift: jest.fn(() =>
        of(
          opts.expired
            ? {
                shift: {
                  id: 'shift-expired',
                  prop_id: 1,
                  shift_type: 'morning',
                  employee: 'Recepcionista',
                  start_time: new Date(Date.now() - 15 * 3600_000).toISOString(),
                  cash_initial: 100,
                  total_collected: 0,
                  status: 'open',
                  transactions: [],
                  is_expired: true,
                  max_open_hours: 12,
                  expires_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
                },
                shift_type_labels: CUSTOM_CONFIG.labels,
              }
            : {
                shift: opts.openedBy
                  ? {
                      id: 'shift-active',
                      prop_id: 1,
                      shift_type: 'morning',
                      employee: 'Recepcionista',
                      opened_by: opts.openedBy,
                      start_time: opts.openedAt ?? new Date().toISOString(),
                      cash_initial: 100,
                      total_collected: 0,
                      status: 'open',
                      transactions: [],
                      ...opts.shift,
                    }
                  : null,
                shift_type_labels: CUSTOM_CONFIG.labels,
              },
        ),
      ),
      getShiftConfig: apiOverrides.getShiftConfig ?? jest.fn(() => of({ config: CUSTOM_CONFIG })),
      updateShiftConfig: jest.fn(() => of({ config: CUSTOM_CONFIG, message: 'Ventanas de turno actualizadas' })),
      listShifts: jest.fn(() => of({ items: [], total: 0 })),
      openShift: jest.fn(() => of({ shift: {}, message: '' })),
      closeShift: jest.fn(() => of({ shift: {}, message: '', summary: {} })),
      listShiftsForCashControl: jest.fn(() => of({ items: [], total: 0 })),
      getShift: jest.fn(() => of({ shift: {} })),
    } as unknown as ShiftsApiService;
    const auth = {
      hasPermission: jest.fn((p: string) => (opts.canManage === false ? p !== 'shifts.manage' : true)),
    } as unknown as AuthService;

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [ControlTurnosCajaPageComponent],
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
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: ShiftsApiService, useValue: api },
        { provide: AuthService, useValue: auth },
      ],
    });

    const fixture = TestBed.createComponent(ControlTurnosCajaPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, toast: TestBed.inject(ToastService), api, auth };
  }

  it('carga las ventanas configuradas y las usa en el select de tipo de turno', () => {
    const { component } = setup();

    expect(component.shiftTypeLabels()).toEqual(CUSTOM_CONFIG.labels);
    expect(component.shiftTypeOptions()).toContainEqual({
      value: 'morning',
      label: 'Matutino (10:00-18:00)',
    });
  });

  it('muestra el botón de configuración solo con shifts.manage', () => {
    const noPerm = setup({ canManage: false });
    const text = noPerm.fixture.nativeElement.textContent as string;
    expect(text).not.toContain('Configurar ventanas');

    const withPerm = setup();
    const buttons = Array.from(withPerm.fixture.nativeElement.querySelectorAll('button'));
    expect(buttons.some(b => b.textContent?.includes('Configurar ventanas'))).toBe(true);
  });

  it('abre el modal con las ventanas actuales precargadas', () => {
    const { component, fixture } = setup();

    component.openConfigModal();
    fixture.detectChanges();

    expect(component.showConfigModal()).toBe(true);
    expect(component.configDraft()).toEqual(CUSTOM_CONFIG.windows);
    const inputs = fixture.nativeElement.querySelectorAll('.sc-config-row input[type="time"]');
    expect(inputs.length).toBe(6);
  });

  it('muestra en el modal quién y cuándo hizo el último cambio (hint de auditoría)', () => {
    const { component, fixture } = setup();

    component.openConfigModal();
    fixture.detectChanges();

    const hint = fixture.nativeElement.querySelector('.sc-modal-config .sc-config-hint');
    expect(hint).not.toBeNull();
    expect(hint.textContent).toContain('Último cambio');
    expect(hint.textContent).toContain('gerente_test');
    expect(hint.textContent).toContain('09/08/2026 19:06');
    expect(hint.querySelector('.material-symbols-outlined')).not.toBeNull();
  });

  it('muestra el estado por defecto en el hint cuando no hay configuración personalizada', () => {
    const { component, fixture } = setup({}, {
      getShiftConfig: jest.fn(() => of({ config: { ...CUSTOM_CONFIG, is_custom: false, updated_by: null, updated_at: null } })),
    });

    component.openConfigModal();
    fixture.detectChanges();

    const hint = fixture.nativeElement.querySelector('.sc-modal-config .sc-config-hint');
    expect(hint).not.toBeNull();
    expect(hint.textContent).toContain('Ventanas por defecto');
    expect(hint.textContent).not.toContain('Último cambio');
  });

  it('muestra en el formulario de apertura quién y cuándo cerró el último turno (hint de auditoría)', () => {
    const { component, fixture, api } = setup();
    (api.listShifts as jest.Mock).mockReturnValue(
      of({
        items: [
          {
            id: 'shift-prev',
            prop_id: 1,
            shift_type: 'afternoon',
            employee: 'Cajera Anterior',
            start_time: '2026-08-09T06:00:00.000000',
            end_time: '2026-08-09T14:30:00.000000',
            status: 'closed',
            closed_by: 'cajera_prev',
            closed_at: '2026-08-09T14:30:00.000000',
            cash_left: 80,
            cash_initial: 50,
            total_collected: 0,
            transactions: [],
          },
        ],
        total: 1,
      }),
    );

    component.openOpenForm();
    fixture.detectChanges();

    const hint = fixture.nativeElement.querySelector('.sc-open-form .sc-config-hint');
    expect(hint).not.toBeNull();
    expect(hint.textContent).toContain('Último cierre');
    expect(hint.textContent).toContain('cajera_prev');
    expect(hint.textContent).toContain('09/08/2026 14:30');
    expect(hint.querySelector('.material-symbols-outlined')).not.toBeNull();
  });

  it('muestra en el modal de cierre quién y cuándo abrió el turno (hint de auditoría)', () => {
    const { component, fixture } = setup({
      openedBy: 'cajero_actual',
      openedAt: '2026-08-09T06:00:00.000000',
    });

    component.openCloseModal();
    fixture.detectChanges();

    const hint = fixture.nativeElement.querySelector('.sc-close-summary-preview .sc-config-hint');
    expect(hint).not.toBeNull();
    expect(hint.textContent).toContain('Apertura');
    expect(hint.textContent).toContain('cajero_actual');
    expect(hint.textContent).toContain('09/08/2026 06:00');
  });

  it('guarda las ventanas editadas y actualiza las etiquetas', () => {
    const { component, fixture, api } = setup();

    component.openConfigModal();
    component.setConfigWindow('morning', 'start', '09:00');
    fixture.detectChanges();

    const updated: ShiftConfig = {
      ...CUSTOM_CONFIG,
      windows: { ...CUSTOM_CONFIG.windows, morning: { start: '09:00', end: '18:00' } },
      labels: { ...CUSTOM_CONFIG.labels, morning: 'Matutino (09:00-18:00)' },
    };
    (api.updateShiftConfig as jest.Mock).mockReturnValue(of({ config: updated, message: 'Ventanas de turno actualizadas' }));

    component.saveShiftConfig();

    expect(api.updateShiftConfig).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ morning: { start: '09:00', end: '18:00' } }),
      CUSTOM_CONFIG.max_open_hours,
      CUSTOM_CONFIG.notify_manager_hours,
    );
    expect(component.showConfigModal()).toBe(false);
    expect(component.shiftTypeLabels().morning).toBe('Matutino (09:00-18:00)');
  });

  it('muestra el error de validación del servidor en el modal', () => {
    const { component, fixture, api } = setup();

    component.openConfigModal();
    (api.updateShiftConfig as jest.Mock).mockReturnValue(
      throwError(() => ({
        status: 400,
        message: 'Las ventanas de morning y afternoon se superponen',
        details: { detail: 'Las ventanas de morning y afternoon se superponen' },
      })),
    );

    component.saveShiftConfig();
    fixture.detectChanges();

    expect(component.configError()).toBe('Las ventanas de morning y afternoon se superponen');
  });

  it('precarga el límite de horas abierto del hotel en el modal de configuración', () => {
    const { component } = setup();

    component.openConfigModal();

    expect(component.configMaxOpenHours()).toBe(6);
  });

  it('envía el límite de horas al guardar la configuración', () => {
    const { component, api } = setup();

    component.openConfigModal();
    component.configMaxOpenHours.set(8);
    component.saveShiftConfig();

    expect(api.updateShiftConfig).toHaveBeenCalledWith(
      1,
      expect.anything(),
      8,
      expect.anything(),
    );
  });

  it('precarga el aviso al gerente del hotel en el modal de configuración', () => {
    const { component } = setup();

    component.openConfigModal();

    expect(component.configNotifyHours()).toBe(5);
  });

  it('envía el aviso al gerente al guardar la configuración', () => {
    const { component, api } = setup();

    component.openConfigModal();
    component.configNotifyHours.set(6);
    component.saveShiftConfig();

    expect(api.updateShiftConfig).toHaveBeenCalledWith(
      1,
      expect.anything(),
      expect.anything(),
      6,
    );
  });

  it('muestra la alerta de turno vencido cuando el turno activo superó el límite', () => {
    const api = {
      getActiveShift: jest.fn(() =>
        of({
          shift: {
            id: 'shift-expired',
            prop_id: 1,
            shift_type: 'morning',
            employee: 'Recepcionista',
            start_time: new Date(Date.now() - 15 * 3600_000).toISOString(),
            cash_initial: 100,
            total_collected: 0,
            status: 'open',
            transactions: [],
            is_expired: true,
            max_open_hours: 12,
            expires_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
          },
          shift_type_labels: CUSTOM_CONFIG.labels,
        }),
      ),
      getShiftConfig: jest.fn(() => of({ config: CUSTOM_CONFIG })),
      updateShiftConfig: jest.fn(() => of({ config: CUSTOM_CONFIG, message: 'Ventanas de turno actualizadas' })),
      listShifts: jest.fn(() => of({ items: [], total: 0 })),
      openShift: jest.fn(() => of({ shift: {}, message: '' })),
      closeShift: jest.fn(() => of({ shift: {}, message: '', summary: {} })),
      listShiftsForCashControl: jest.fn(() => of({ items: [], total: 0 })),
      getShift: jest.fn(() => of({ shift: {} })),
    } as unknown as ShiftsApiService;

    const propertyContext = {
      ready: signal(false),
      singleHotelMode: signal(false),
      currentPropId: signal(1),
      currentCurrency: signal('USD'),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [ControlTurnosCajaPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: Router,
          useValue: {
            events: new Subject<unknown>().asObservable(),
            navigate: jest.fn(),
          } as unknown as Router,
        },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: ShiftsApiService, useValue: api },
        {
          provide: AuthService,
          useValue: { hasPermission: jest.fn(() => true) } as unknown as AuthService,
        },
      ],
    });

    const fixture = TestBed.createComponent(ControlTurnosCajaPageComponent);
    fixture.detectChanges();

    expect(fixture.componentInstance.shift()?.is_expired).toBe(true);
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('sin cerrarse');
    expect(text).toContain('bloqueadas');
  });

  it('muestra la sección de cierre de emergencia para turnos vencidos con shifts.manage', () => {
    const { component, fixture } = setup({ expired: true });

    component.openCloseModal();
    fixture.detectChanges();

    expect(component.canEmergencyClose()).toBe(true);
    let text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Cierre de emergencia');

    // Activating the toggle reveals the reason field (placeholder default).
    component.emergencyClose.set(true);
    fixture.detectChanges();
    text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Motivo del cierre de emergencia');
    const reasonInput = fixture.nativeElement.querySelector('#sc-emergency-reason') as HTMLInputElement;
    expect(reasonInput).not.toBeNull();
    expect(reasonInput.placeholder).toBe('vencimiento');
  });

  it('oculta el cierre de emergencia sin shifts.manage', () => {
    const { component, fixture } = setup({ expired: true, canManage: false });

    component.openCloseModal();
    fixture.detectChanges();

    expect(component.canEmergencyClose()).toBe(false);
    const text = fixture.nativeElement.textContent as string;
    expect(text).not.toContain('Cierre de emergencia');
  });

  it('envía emergency y motivo al cerrar un turno vencido', () => {
    const { component, api } = setup({ expired: true });

    component.openCloseModal();
    component.emergencyClose.set(true);
    component.emergencyReason.set('Caja desincronizada por corte de luz');
    component.closeCashCounted.set(100);
    component.confirmCloseShift();

    expect(api.closeShift).toHaveBeenCalledWith(
      'shift-expired',
      100,
      expect.anything(),
      undefined,
      '',
      undefined,
      true,
      'Caja desincronizada por corte de luz',
    );
  });

  // ═══ Drawer unificado: pagos estampados visibles en el arqueo en vivo ═══

  it('muestra el conteo de pagos estampados y el breakdown unificado en el arqueo', () => {
    const { fixture } = setup({
      openedBy: 'Recepcionista',
      shift: {
        payment_breakdown: { cash: 45, card: 0, transfer: 0, other: 0, total: 45 },
        stamped_payments_count: 1,
      },
    });
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    // Breakdown unificado: el depósito estampado aparece como ingreso
    expect(text).toContain('+$45.00');
    // Fila de pagos de sistema + conteo en el header de auditoría
    expect(text).toContain('Pagos registrados en sistema');
    expect(text).toContain('+1 pagos');
    expect(text).toContain('· 1 pagos de sistema');
  });

  it('NO muestra la fila de pagos estampados cuando no hay ninguno', () => {
    const { fixture } = setup({ openedBy: 'Recepcionista' });
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).not.toContain('Pagos registrados en sistema');
    expect(text).not.toContain('pagos de sistema');
  });
});
