import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { ToastService } from '../../../../shared/services/toast.service';
import { OperationModeService, type OperationMode } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { M2cConsolidatedDto, M2cActionResponseDto, M2cRefreshMode } from '../../models/monitoring-m2c.dto';
import { MonitoringM2cApiService } from '../../services/monitoring-m2c-api.service';

@Component({
  selector: 'app-monitoring-m2c-page',
  imports: [
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
    DecimalPipe,
  ],
  templateUrl: './monitoring-m2c-page.html',
  styleUrl: './monitoring-m2c-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonitoringM2cPageComponent {
  private readonly api = inject(MonitoringM2cApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly toast = inject(ToastService);
  private readonly opMode = inject(OperationModeService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  readonly monitoringResource = httpResource<M2cConsolidatedDto>(() => '/api/etl-status/m2c/consolidated');

  readonly viewModel = this.monitoringResource.value;

  readonly isRunning = computed(() => this.viewModel()?.progress.is_running ?? false);

  readonly dato = computed(() => this.viewModel()?.dato);

  /** Secciones del directorio Dato con conteos legibles para la UI. */
  readonly datoSections = computed(() => {
    const dato = this.dato();
    if (!dato) return [];
    return (['Crudo', 'Procesado', 'Terminado'] as const)
      .filter(section => dato.sections[section])
      .map(section => {
        const tables = Object.entries(dato.sections[section]).map(([name, rows]) => ({
          name,
          rows: Number(rows) || 0,
        }));
        return {
          key: section,
          files: tables.length,
          rows: tables.reduce((total, table) => total + table.rows, 0),
          tables,
        };
      });
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.monitoringResource.isLoading()) return 'loading';
    if (this.monitoringResource.error()) return 'error';
    return 'success';
  });

  readonly loadErrorMessage = computed(() => {
    const err = this.monitoringResource.error();
    return (err as unknown as ApiError)?.message || '';
  });

  readonly actionBusy = signal(false);
  readonly actionMessage = signal('');
  readonly actionError = signal('');
  readonly openSection = signal<string | null>('schedule');
  readonly scheduleCron = signal('');
  readonly scheduleEnabled = signal(true);
  readonly scheduleFrequency = signal<'hourly' | 'daily'>('hourly');
  readonly scheduleMinute = signal('0');
  readonly scheduleTime = signal('00:00');
  /** Modo de refresco de los KPIs: 'full' (barrido) o 'incremental' (solo cambios). */
  readonly refreshMode = signal<M2cRefreshMode>('full');
  readonly stepOrder = [
    'validate_config',
    'extract_mongo',
    'transform',
    'create_tables',
    'load_clickhouse',
    'quality_report',
    'execution_report',
  ] as const;
  /** Acción ETL pendiente de confirmar — mantiene el modo 'execute' en el nav. */
  private readonly pendingAction = signal<{ title: string } | null>(null);

  /**
   * Modo CRUD de la página M2C: fuera del flujo CRUD normal. Muestra 'execute'
   * (Ejecutando) mientras hay un diálogo de confirmación abierto o el ETL corre;
   * en reposo, Solo lectura.
   */
  private readonly _opMode = computed<{ mode: OperationMode; detail: string }>(() => {
    const pending = this.pendingAction();
    if (pending) return { mode: 'execute', detail: pending.title };
    if (this.isRunning()) return { mode: 'execute', detail: 'ETL Mongo → ClickHouse' };
    return { mode: 'read', detail: '' };
  });

  constructor() {
    this.destroyRef.onDestroy(() => this.stopPolling());

    effect(() => {
      const vm = this.viewModel();
      if (!vm) return;
      this.scheduleCron.set(vm.schedule.schedule_cron);
      this.scheduleEnabled.set(vm.schedule.enabled);
      this.refreshMode.set(vm.schedule.refresh_mode ?? 'full');
      this.syncScheduleControls(vm.schedule.schedule_cron);
    });

    effect(() => {
      if (this.isRunning()) {
        this.startPolling();
      } else {
        this.stopPolling();
      }
    });

    // Modo CRUD reactivo en el nav: execute con diálogo abierto o ETL corriendo.
    effect(() => {
      const m = this._opMode();
      this.opMode.setMode(m.mode, m.detail);
    });
  }

  private startPolling() {
    this.stopPolling();
    this.pollTimer = setInterval(() => this.monitoringResource.reload(), 1000);
  }

  private stopPolling() {
    if (this.pollTimer !== null) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  toggleSection(key: string) {
    this.openSection.update(v => v === key ? null : key);
  }

  /**
   * Abre el diálogo de confirmación GLOBAL (ConfirmDialogService) para una
   * acción ETL. Mientras está abierto, el nav muestra el modo 'execute' con el
   * título de la acción; al resolver (confirmar o cancelar) se restaura.
   */
  private openConfirm(
    title: string,
    message: string,
    action: () => void,
    options: { confirmLabel?: string; variant?: 'danger' | 'warning' | 'default' } = {},
  ): void {
    this.pendingAction.set({ title });
    void this.confirmDialog.open({
      title,
      message,
      confirmLabel: options.confirmLabel ?? 'Continuar',
      cancelLabel: 'Cancelar',
      variant: options.variant ?? 'warning',
    }).then((ok) => {
      this.pendingAction.set(null);
      if (ok) action();
    });
  }

  triggerRun() {
    this.openConfirm(
      'Ejecutar ETL Mongo → ClickHouse',
      'Esta acción ejecutará el pipeline táctico: agrega KPIs desde MongoDB y los carga a ClickHouse (ReplacingMergeTree, idempotente). ¿Desea continuar?',
      () => this.execAction(this.api.triggerRun()),
      { confirmLabel: 'Ejecutar' },
    );
  }

  triggerStop() {
    this.openConfirm(
      'Detener pipeline M2C',
      'Esta acción solicitará la detención de la corrida mongo→clickhouse en curso. ¿Desea continuar?',
      () => this.execAction(this.api.triggerStop()),
      { confirmLabel: 'Detener', variant: 'danger' },
    );
  }

  setScheduleFrequency(frequency: 'hourly' | 'daily') {
    this.scheduleFrequency.set(frequency);
  }

  setRefreshMode(mode: M2cRefreshMode) {
    this.refreshMode.set(mode);
  }

  refreshModeLabel(): string {
    return this.refreshMode() === 'incremental'
      ? 'Incremental — solo data nueva/actualizada'
      : 'Sobrescribir todo — barrido completo';
  }

  private syncScheduleControls(cron: string) {
    const hourly = cron.match(/^(\d{1,2}) \* \* \* \*$/);
    if (hourly) {
      this.scheduleFrequency.set('hourly');
      this.scheduleMinute.set(hourly[1].padStart(2, '0'));
      return;
    }
    const daily = cron.match(/^(\d{1,2}) (\d{1,2}) \* \* \*$/);
    if (daily) {
      this.scheduleFrequency.set('daily');
      this.scheduleTime.set(`${daily[2].padStart(2, '0')}:${daily[1].padStart(2, '0')}`);
      return;
    }
    // Los horarios antiguos/custom no se exponen como sintaxis cron.
    // Se ofrece una opción segura y explícita al guardar.
    this.scheduleFrequency.set('hourly');
    this.scheduleMinute.set('0');
  }

  private cronFromControls(): string {
    if (this.scheduleFrequency() === 'hourly') {
      return `${Number(this.scheduleMinute())} * * * *`;
    }
    const [hour, minute] = this.scheduleTime().split(':');
    return `${Number(minute)} ${Number(hour)} * * *`;
  }

  scheduleSummary(): string {
    if (this.scheduleFrequency() === 'hourly') {
      return `Cada hora, en el minuto ${this.scheduleMinute()}`;
    }
    return `Cada día a las ${this.scheduleTime()}`;
  }

  saveSchedule() {
    const cron = this.cronFromControls();
    this.scheduleCron.set(cron);
    this.openConfirm(
      'Actualizar horario del DAG',
      `El DAG se ejecutará ${this.scheduleSummary().toLowerCase()} (${this.scheduleEnabled() ? 'habilitado' : 'pausado'}) en modo ${this.refreshModeLabel().toLowerCase()}. Se aplica en el próximo parseo de Airflow. ¿Desea continuar?`,
      () => {
        this.actionBusy.set(true);
        this.api.updateSchedule({
          schedule_cron: cron,
          enabled: this.scheduleEnabled(),
          refresh_mode: this.refreshMode(),
        }).subscribe({
          next: (result) => {
            this.actionBusy.set(false);
            if (result.ok) {
              this.actionMessage.set(result.display_message);
              this.toast.show(result.display_message, 'info', 5000);
              setTimeout(() => this.monitoringResource.reload(), 300);
            } else {
              this.actionError.set(result.display_message);
            }
          },
          error: (err: ApiError) => {
            this.actionBusy.set(false);
            const msg = err.message || 'Error al actualizar el horario.';
            this.actionError.set(msg);
            this.toast.show(msg, 'error', 5000);
          },
        });
      },
      { confirmLabel: 'Guardar' },
    );
  }

  refresh() {
    this.actionMessage.set('');
    this.actionError.set('');
    this.monitoringResource.reload();
  }

  executionMetrics(payload: Record<string, unknown>): Record<string, unknown> {
    return this.asRecord(payload['metrics']);
  }

  executionQuality(payload: Record<string, unknown>): Record<string, unknown> {
    return this.asRecord(payload['quality']);
  }

  executionRows(payload: Record<string, unknown>): Array<{ name: string; loaded: number; state: string }> {
    const metrics = this.executionMetrics(payload);
    const quality = this.executionQuality(payload);
    const rows = this.asRecord(metrics['rows_by_table']);
    const qualityTables = this.asRecord(quality['tables']);
    return Object.entries(rows).map(([name, value]) => {
      const tableQuality = this.asRecord(qualityTables[name]);
      return {
        name,
        loaded: Number(value) || 0,
        state: String(tableQuality['state'] ?? 'unknown'),
      };
    });
  }

  executionTotalRows(payload: Record<string, unknown>): number {
    return this.executionRows(payload).reduce((total, row) => total + row.loaded, 0);
  }

  executionDate(value: unknown): string {
    if (!value) return '—';
    const date = new Date(String(value));
    if (Number.isNaN(date.getTime()) || date.getUTCFullYear() < 2000) return 'No disponible';
    return new Intl.DateTimeFormat('es-ES', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  }

  executionDuration(value: unknown): string {
    const milliseconds = Number(value);
    if (!Number.isFinite(milliseconds)) return '—';
    if (milliseconds < 1000) return `${Math.round(milliseconds)} ms`;
    return `${(milliseconds / 1000).toFixed(1)} s`;
  }

  executionStatus(payload: Record<string, unknown>): string {
    return String(payload['status'] ?? 'unknown');
  }

  executionRefreshMode(payload: Record<string, unknown>): string {
    const mode = String(this.executionMetrics(payload)['refresh_mode'] ?? 'full');
    if (mode === 'full') return 'Sobrescribir todo (barrido)';
    if (mode === 'incremental') return 'Incremental (solo cambios)';
    if (mode === 'aggregate_refresh') return 'Recomposición de agregados';
    return mode;
  }

  private asRecord(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {};
  }

  statusTone(status: string): 'success' | 'warning' | 'danger' {
    if (status === 'completed' || status === 'success') return 'success';
    if (status === 'failed') return 'danger';
    return 'warning';
  }

  private execAction(action: { subscribe: (observer: { next: (r: M2cActionResponseDto) => void; error: (e: ApiError) => void }) => void }) {
    this.actionMessage.set('');
    this.actionError.set('');
    this.actionBusy.set(true);
    action.subscribe({
      next: (result: M2cActionResponseDto) => {
        this.actionBusy.set(false);
        if (result.ok) {
          this.actionMessage.set(result.display_message);
          this.toast.show(result.display_message, 'info', 5000);
          setTimeout(() => this.monitoringResource.reload(), 500);
        } else {
          this.actionError.set(result.display_message);
          this.toast.show(result.display_message + (result.summary_output ? ' — ' + result.summary_output : ''), 'error', 6000);
        }
      },
      error: (err: ApiError) => {
        this.actionBusy.set(false);
        const msg = err.message || 'Error al ejecutar la acción.';
        this.actionError.set(msg);
        this.toast.show(msg, 'error', 5000);
      },
    });
  }
}
