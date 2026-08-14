import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, Subject } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { MonitoringM2cApiService } from '../../services/monitoring-m2c-api.service';
import type { M2cConsolidatedDto } from '../../models/monitoring-m2c.dto';
import { MonitoringM2cPageComponent } from './monitoring-m2c-page';

function makeM2c(running = false): M2cConsolidatedDto {
  return {
    services: { clickhouse: { available: true, database: 'hoteldata_analytics', tables: [], message: 'Disponible' } },
    schedule: {
      pipeline: 'mongo_to_clickhouse', schedule_cron: '0 * * * *', enabled: true, configured: true,
      refresh_mode: 'full', updated_at: '', updated_by: '',
    },
    progress: {
      exists: true, path: '', status: running ? 'running' : 'pending', section: '', percent: 0, elapsed_ms: 0,
      message: '', detail: {}, updated_at: '', sections: {}, is_running: running,
      clickhouse_database: 'hoteldata_analytics', tables: [],
    },
    execution: { exists: false, path: '', payload: {} },
    dato: {
      exists: false, root: '', container_path: '', run_date: '', sections: {}, generated_at: '',
    },
  };
}

describe('MonitoringM2cPageComponent — modo CRUD del nav (execute ETL)', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as never;

    const api = { triggerRun: jest.fn(), triggerStop: jest.fn(), updateSchedule: jest.fn() };
    const toast = { show: jest.fn(), success: jest.fn(), error: jest.fn() };

    TestBed.configureTestingModule({
      imports: [MonitoringM2cPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        { provide: MonitoringM2cApiService, useValue: api },
        { provide: ToastService, useValue: toast },
      ],
    });

    const fixture = TestBed.createComponent(MonitoringM2cPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      mode: TestBed.inject(OperationModeService),
      confirmDialog: TestBed.inject(ConfirmDialogService),
      http: TestBed.inject(HttpTestingController),
      api,
    };
  }

  async function seed(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }, dto: M2cConsolidatedDto) {
    ctx.http.expectOne('/api/etl-status/m2c/consolidated').flush(dto);
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

  it('parte en Solo lectura al cargar', () => {
    const { mode } = setup();
    expect(mode.mode()).toBe('read');
  });

  it('muestra Ejecutando al abrir el diálogo de confirmación global (Ejecutar ETL)', () => {
    const { component, mode, confirmDialog, fixture } = setup();

    component.triggerRun();
    fixture.detectChanges();

    expect(confirmDialog.isOpen()).toBe(true);
    expect(mode.mode()).toBe('execute');
    expect(mode.detail()).toBe('Ejecutar ETL Mongo → ClickHouse');
  });

  it('al confirmar ejecuta la acción y vuelve a Solo lectura', async () => {
    const { component, mode, confirmDialog, api, fixture } = setup();
    api.triggerRun.mockReturnValue(of({ ok: true, display_message: 'ETL iniciado', summary_output: '' }));

    component.triggerRun();
    fixture.detectChanges();
    expect(mode.mode()).toBe('execute');

    confirmDialog.confirm();
    await flush();
    fixture.detectChanges();

    expect(api.triggerRun).toHaveBeenCalled();
    expect(mode.mode()).toBe('read');
  });

  it('muestra Ejecutando mientras el ETL corre', async () => {
    const ctx = setup();
    await seed(ctx, makeM2c(true));

    expect(ctx.mode.mode()).toBe('execute');
    expect(ctx.mode.detail()).toBe('ETL Mongo → ClickHouse');
  });

  it('sincroniza refreshMode desde el schedule del consolidated', async () => {
    const ctx = setup();
    const dto = makeM2c();
    dto.schedule.refresh_mode = 'incremental';
    await seed(ctx, dto);

    expect(ctx.component.refreshMode()).toBe('incremental');
  });

  it('envía el refresh_mode elegido al guardar el horario', async () => {
    const { component, confirmDialog, api, fixture } = setup();
    api.updateSchedule.mockReturnValue(of({ ok: true, display_message: 'ok', summary_output: '' }));
    component.refreshMode.set('incremental');

    component.saveSchedule();
    fixture.detectChanges();
    expect(confirmDialog.isOpen()).toBe(true);

    confirmDialog.confirm();
    await flush();
    fixture.detectChanges();

    expect(api.updateSchedule).toHaveBeenCalledWith(
      expect.objectContaining({ refresh_mode: 'incremental', enabled: true }),
    );
  });

  it('expone las secciones del directorio Dato con sus conteos de parquet', async () => {
    const ctx = setup();
    const dto = makeM2c();
    dto.dato = {
      exists: true,
      root: 'C:\\HotelData\\Dato',
      container_path: '/app/dato',
      run_date: '2026-08-09',
      sections: {
        Crudo: { kpi_booking_daily: 3, kpi_rate_daily: 1 },
        Procesado: { kpi_booking_daily: 2 },
        Terminado: { kpi_booking_daily: 2 },
      },
      generated_at: '2026-08-09T17:00:00Z',
    };
    await seed(ctx, dto);

    const sections = ctx.component.datoSections();
    expect(sections.map(s => s.key)).toEqual(['Crudo', 'Procesado', 'Terminado']);
    expect(sections[0].files).toBe(2);
    expect(sections[0].rows).toBe(4);
    expect(sections[0].tables).toEqual([
      { name: 'kpi_booking_daily', rows: 3 },
      { name: 'kpi_rate_daily', rows: 1 },
    ]);
  });
});
