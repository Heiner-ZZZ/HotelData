import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ToastService } from '../../../../shared/services/toast.service';
import { OperationModeService, type OperationMode } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { MonitoringViewModel } from '../../models/monitoring.model';
import type { ConsolidatedMonitoringDto } from '../../models/monitoring.dto';
import { MonitoringApiService } from '../../services/monitoring-api.service';
import { mapConsolidatedMonitoringData } from '../../mappers/monitoring.mapper';
import { MpCsvUploadBoxComponent } from './partials/mp-csv-upload-box';
import { MpEtlProgressBoxComponent } from './partials/mp-etl-progress-box';
import { MpExecutionBoxComponent } from './partials/mp-execution-box';
import { MpReportsBoxComponent } from './partials/mp-reports-box';
import { MpServicesBoxComponent } from './partials/mp-services-box';

import type { Observable } from 'rxjs';
import type { ActionResponseDto } from '../../models/monitoring.dto';

@Component({
  selector: 'app-monitoring-page',
  imports: [
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    MpCsvUploadBoxComponent,
    MpEtlProgressBoxComponent,
    MpExecutionBoxComponent,
    MpReportsBoxComponent,
    MpServicesBoxComponent,
  ],
  templateUrl: './monitoring-page.html',
  styleUrl: './monitoring-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonitoringPageComponent {
  private readonly api = inject(MonitoringApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly toast = inject(ToastService);
  private readonly opMode = inject(OperationModeService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  readonly monitoringResource = httpResource<MonitoringViewModel>(() => '/api/etl-status/consolidated', {
    parse: (dto) => mapConsolidatedMonitoringData(dto as ConsolidatedMonitoringDto),
  });

  readonly viewModel = this.monitoringResource.value;

  readonly isRunning = computed(() => this.viewModel()?.progress.isRunning ?? false);

  readonly viewState = computed<ViewState>(() => {
    if (this.monitoringResource.isLoading()) return 'loading';
    if (this.monitoringResource.error()) return 'error';
    return 'success';
  });

  readonly loadErrorMessage = computed(() => {
    const err = this.monitoringResource.error();
    return (err as unknown as ApiError)?.message || '';
  });

  readonly actionMessage = signal('');
  readonly actionError = signal('');
  readonly actionBusy = signal(false);

  readonly selectedFile = signal<File | null>(null);
  readonly uploadBusy = signal(false);
  readonly targetPocketbase = signal(300000);
  readonly targetMongodb = signal(300000);
  /** Acción ETL pendiente de confirmar — mantiene el modo 'execute' en el nav. */
  private readonly pendingAction = signal<{ title: string } | null>(null);

  readonly incrementalMode = signal(false);

  /**
   * Modo CRUD de la página de monitoreo: fuera del flujo CRUD normal. Muestra
   * 'execute' (Ejecutando) mientras hay un diálogo de confirmación ETL abierto
   * o mientras el proceso está corriendo; en reposo, Solo lectura.
   */
  private readonly _opMode = computed<{ mode: OperationMode; detail: string }>(() => {
    const pending = this.pendingAction();
    if (pending) return { mode: 'execute', detail: pending.title };
    if (this.isRunning()) {
      const vm = this.viewModel();
      if (vm?.progress.preparationStatus === 'running') return { mode: 'execute', detail: 'Preparación GA03' };
      if (vm?.progress.pipelineStatus === 'running') return { mode: 'execute', detail: 'Pipeline GA03' };
      return { mode: 'execute', detail: 'ETL GA03' };
    }
    return { mode: 'read', detail: '' };
  });

  constructor() {
    this.destroyRef.onDestroy(() => this.stopPolling());

    effect(() => {
      const vm = this.viewModel();
      if (!vm) return;

      if (vm.progress.preparationTarget > 0) {
        this.targetPocketbase.set(vm.progress.preparationTarget);
      }
      if (vm.progress.pipelineTarget > 0) {
        this.targetMongodb.set(vm.progress.pipelineTarget);
      }
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

  onFileSelected(file: File) {
    this.selectedFile.set(file);
  }

  uploadCsv() {
    const file = this.selectedFile();
    if (!file) return;
    this.uploadBusy.set(true);
    this.actionMessage.set('');
    this.actionError.set('');
    this.api.uploadCsv(file).subscribe({
      next: (result) => {
        this.uploadBusy.set(false);
        this.selectedFile.set(null);
        this.actionMessage.set(result.display_message);
        this.toast.show(result.display_message, 'info', 5000);
        setTimeout(() => this.monitoringResource.reload(), 300);
      },
      error: (err: ApiError) => {
        this.uploadBusy.set(false);
        const msg = err.message || 'Error al subir el archivo.';
        this.actionError.set(msg);
        this.toast.show(msg, 'error', 5000);
      },
    });
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

  triggerValidate() {
    this.openConfirm(
      'Validar dataset GA03',
      'Esta acción verificará que PocketBase tenga los registros objetivo y que MongoDB esté disponible. No modifica datos. ¿Desea continuar?',
      () => this.execAction(this.api.triggerValidate(this.targetPocketbase())),
      { confirmLabel: 'Validar' },
    );
  }

  triggerRunPipeline() {
    const mode = this.incrementalMode();
    const modeLabel = mode ? 'incremental' : 'completo (full reload)';
    this.openConfirm(
      'Ejecutar pipeline GA03',
      `Esta acción ejecutará el ETL principal PocketBase → JSONL → Parquet → MongoDB en modo ${modeLabel}. ¿Desea continuar?`,
      () => this.execAction(this.api.triggerRunPipeline(this.targetMongodb(), mode)),
      { confirmLabel: 'Ejecutar' },
    );
  }

  triggerSeed() {
    const mode = this.incrementalMode();
    const modeLabel = mode ? 'incremental' : 'completo (full reload)';
    this.openConfirm(
      'Preparar fuente GA03',
      `Esta acción cargará registros desde CSV hacia PocketBase hotel_reservation_events_03 en modo ${modeLabel}. No carga directo a MongoDB. ¿Desea continuar?`,
      () => this.execAction(this.api.triggerSeed(this.targetPocketbase(), mode)),
      { confirmLabel: 'Preparar' },
    );
  }

  triggerClearEvidence() {
    this.openConfirm(
      'Limpiar evidencia local GA03',
      'Esta acción eliminará reportes, logs, .parquet, .jsonl y .json generados por el ETL GA03. Los datos en MongoDB se conservan y solo se sobrescriben al re-ejecutar el pipeline. No toca PocketBase. ¿Desea continuar?',
      () => this.execAction(this.api.triggerClearEvidence()),
      { confirmLabel: 'Limpiar', variant: 'danger' },
    );
  }

  triggerStop(process: string) {
    const label = process === 'seed' ? 'Preparación' : 'Pipeline';
    this.openConfirm(
      `Detener ${label}`,
      `Esta acción detendrá el proceso de ${label} GA03 en ejecución. ¿Desea continuar?`,
      () => this.execAction(this.api.triggerStop(process)),
      { confirmLabel: 'Detener', variant: 'danger' },
    );
  }

  refresh() {
    this.actionMessage.set('');
    this.actionError.set('');
    this.monitoringResource.reload();
  }

  private execAction(action: Observable<ActionResponseDto>) {
    this.actionMessage.set('');
    this.actionError.set('');
    this.actionBusy.set(true);
    action.subscribe({
      next: (result: ActionResponseDto) => {
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
