import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, Subject } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { MonitoringApiService } from '../../services/monitoring-api.service';
import type { ConsolidatedMonitoringDto } from '../../models/monitoring.dto';
import { MonitoringPageComponent } from './monitoring-page';

/** DTO consolidado mínimo del ETL GA03 (el mapper tolera lo que falta). */
function makeConsolidated(runningPipeline = false): ConsolidatedMonitoringDto {
  return {
    services: {
      config: {
        task_number: 'GA03',
        target_records: 300000,
        target_records_pb: 300000,
        target_records_mongo: 300000,
        pocketbase_collection: 'hotel_reservation_events_03',
        source_csv_exists: false,
        source_csv: 'reservas_ga03.csv',
        source_csv_resolved: '/data/reservas_ga03.csv',
      },
      pocketbase: { available: true, collection: 'hotel_reservation_events_03', count: 0, state: 'ready', message: 'Disponible' },
      mongodb: { available: true, database: 'hoteldata', fact_exists: false, fact_count: 0, ga03_fact_count: 0, message: 'Disponible' },
      artifacts: {
        jsonl: { exists: false, path: '/data/events.jsonl' },
        parquet: { exists: false, path: '/data/events.parquet' },
      },
    },
    reports: {},
    progress: {
      preparation: {
        exists: false, status: 'idle', loaded_records: 0, target_records: 300000, remaining_records: 300000,
        percent: 0, message: '', is_running: false,
      },
      pipeline: {
        exists: false, status: runningPipeline ? 'running' : 'idle', section: '', percent: runningPipeline ? 10 : 0,
        elapsed_ms: 0, message: '', sections: {}, is_running: runningPipeline, target_records: 0,
      },
    },
    execution: { available: false, source: 'ga03' },
  };
}

describe('MonitoringPageComponent — modo CRUD del nav (execute ETL)', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as never;

    const api = {
      triggerValidate: jest.fn(),
      triggerRunPipeline: jest.fn(),
      triggerSeed: jest.fn(),
      triggerClearEvidence: jest.fn(),
      triggerStop: jest.fn(),
      uploadCsv: jest.fn(),
    };
    const toast = { show: jest.fn(), success: jest.fn(), error: jest.fn() };

    TestBed.configureTestingModule({
      imports: [MonitoringPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        { provide: MonitoringApiService, useValue: api },
        { provide: ToastService, useValue: toast },
      ],
    });

    const fixture = TestBed.createComponent(MonitoringPageComponent);
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

  async function seed(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }, dto: ConsolidatedMonitoringDto) {
    ctx.http.expectOne('/api/etl-status/consolidated').flush(dto);
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

  it('parte en Solo lectura al cargar', () => {
    const { mode } = setup();
    expect(mode.mode()).toBe('read');
  });

  it('muestra Ejecutando al abrir el diálogo de confirmación global (Ejecutar pipeline)', () => {
    const { component, mode, confirmDialog, fixture } = setup();

    component.triggerRunPipeline();
    fixture.detectChanges();

    expect(confirmDialog.isOpen()).toBe(true);
    expect(mode.mode()).toBe('execute');
    expect(mode.detail()).toBe('Ejecutar pipeline GA03');
  });

  it('al confirmar ejecuta la acción y vuelve a Solo lectura', async () => {
    const { component, mode, confirmDialog, api, fixture } = setup();
    api.triggerRunPipeline.mockReturnValue(of({ ok: true, display_message: 'Pipeline iniciado', summary_output: '' }));

    component.triggerRunPipeline();
    fixture.detectChanges();
    expect(mode.mode()).toBe('execute');

    confirmDialog.confirm();
    await flush();
    fixture.detectChanges();

    expect(api.triggerRunPipeline).toHaveBeenCalledWith(300000, false);
    expect(mode.mode()).toBe('read');
  });

  it('al cancelar no ejecuta la acción y vuelve a Solo lectura', async () => {
    const { component, mode, confirmDialog, api, fixture } = setup();

    component.triggerValidate();
    fixture.detectChanges();
    expect(mode.mode()).toBe('execute');

    confirmDialog.cancel();
    await flush();
    fixture.detectChanges();

    expect(api.triggerValidate).not.toHaveBeenCalled();
    expect(mode.mode()).toBe('read');
  });

  it('muestra Ejecutando mientras el pipeline ETL corre', async () => {
    const ctx = setup();
    await seed(ctx, makeConsolidated(true));

    expect(ctx.mode.mode()).toBe('execute');
    expect(ctx.mode.detail()).toBe('Pipeline GA03');
  });
});
