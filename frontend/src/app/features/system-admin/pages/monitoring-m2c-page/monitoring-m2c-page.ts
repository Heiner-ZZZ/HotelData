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
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { M2cConsolidatedDto, M2cActionResponseDto } from '../../models/monitoring-m2c.dto';
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
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  readonly monitoringResource = httpResource<M2cConsolidatedDto>(() => '/api/etl-status/m2c/consolidated');

  readonly viewModel = this.monitoringResource.value;

  readonly isRunning = computed(() => this.viewModel()?.progress.is_running ?? false);

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
  readonly stepOrder = [
    'validate_config',
    'extract_mongo',
    'transform',
    'create_tables',
    'load_clickhouse',
    'quality_report',
    'execution_report',
  ] as const;
  readonly confirmAction = signal<{ title: string; message: string; handler: () => void } | null>(null);

  constructor() {
    this.destroyRef.onDestroy(() => this.stopPolling());

    effect(() => {
      const vm = this.viewModel();
      if (!vm) return;
      this.scheduleCron.set(vm.schedule.schedule_cron);
      this.scheduleEnabled.set(vm.schedule.enabled);
      this.syncScheduleControls(vm.schedule.schedule_cron);
    });

    effect(() => {
      if (this.isRunning()) {
        this.startPolling();
      } else {
        this.stopPolling();
      }
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

  triggerRun() {
    this.confirmAction.set({
      title: 'Ejecutar ETL Mongo → ClickHouse',
      message: 'Esta acción ejecutará el pipeline táctico: agrega KPIs desde MongoDB y los carga a ClickHouse (ReplacingMergeTree, idempotente). ¿Desea continuar?',
      handler: () => this.execAction(this.api.triggerRun()),
    });
  }

  triggerStop() {
    this.confirmAction.set({
      title: 'Detener pipeline M2C',
      message: 'Esta acción solicitará la detención de la corrida mongo→clickhouse en curso. ¿Desea continuar?',
      handler: () => this.execAction(this.api.triggerStop()),
    });
  }

  setScheduleFrequency(frequency: 'hourly' | 'daily') {
    this.scheduleFrequency.set(frequency);
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
    this.confirmAction.set({
      title: 'Actualizar horario del DAG',
      message: `El DAG se ejecutará ${this.scheduleSummary().toLowerCase()} (${this.scheduleEnabled() ? 'habilitado' : 'pausado'}). Se aplica en el próximo parseo de Airflow. ¿Desea continuar?`,
      handler: () => {
        this.actionBusy.set(true);
        this.api.updateSchedule({ schedule_cron: cron, enabled: this.scheduleEnabled() }).subscribe({
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
    });
  }

  confirmAccept() {
    const handler = this.confirmAction()?.handler;
    this.confirmAction.set(null);
    if (handler) handler();
  }

  confirmCancel() {
    this.confirmAction.set(null);
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
    const mode = String(this.executionMetrics(payload)['refresh_mode'] ?? 'aggregate_refresh');
    return mode === 'aggregate_refresh' ? 'Recomposición de agregados' : mode;
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
