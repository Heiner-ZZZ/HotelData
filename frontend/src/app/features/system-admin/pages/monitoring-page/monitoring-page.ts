import { ChangeDetectionStrategy, Component, computed, DestroyRef, ElementRef, effect, inject, signal, viewChild } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { InfoTooltipComponent } from '../../../../shared/ui/info-tooltip/info-tooltip.component';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ServiceStatusCard, MonitoringViewModel } from '../../models/monitoring.model';
import type { ConsolidatedMonitoringDto } from '../../models/monitoring.dto';
import { MonitoringApiService } from '../../services/monitoring-api.service';
import { mapConsolidatedMonitoringData } from '../../mappers/monitoring.mapper';

import type { Observable } from 'rxjs';
import type { ActionResponseDto } from '../../models/monitoring.dto';

@Component({
  selector: 'app-monitoring-page',
  imports: [
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    InfoTooltipComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './monitoring-page.html',
  styleUrl: './monitoring-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonitoringPageComponent {
  private readonly api = inject(MonitoringApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly toast = inject(ToastService);
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
  readonly openSection = signal<string | null>(null);
  readonly confirmAction = signal<{ title: string; message: string; handler: () => void } | null>(null);
  readonly targetOptions = Array.from({ length: 16 }, (_, i) => {
    const val = (i + 1) * 100000;
    return { value: val, label: val.toLocaleString('es') };
  });

  readonly incrementalMode = signal(false);
  readonly etlModeLabel = computed(() => this.incrementalMode() ? 'Incremental' : 'Completo');
  readonly fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

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

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.selectedFile.set(input.files[0]);
    }
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
        const nativeInput = this.fileInput()?.nativeElement;
        if (nativeInput) nativeInput.value = '';
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

  triggerValidate() {
    this.confirmAction.set({
      title: 'Validar dataset GA03',
      message: 'Esta acción verificará que PocketBase tenga los registros objetivo y que MongoDB esté disponible. No modifica datos. ¿Desea continuar?',
      handler: () => this.execAction(this.api.triggerValidate(this.targetPocketbase())),
    });
  }

  triggerRunPipeline() {
    const mode = this.incrementalMode();
    const modeLabel = mode ? 'incremental' : 'completo (full reload)';
    this.confirmAction.set({
      title: 'Ejecutar pipeline GA03',
      message: `Esta acción ejecutará el ETL principal PocketBase → JSONL → Parquet → MongoDB en modo ${modeLabel}. ¿Desea continuar?`,
      handler: () => this.execAction(this.api.triggerRunPipeline(this.targetMongodb(), mode)),
    });
  }

  triggerSeed() {
    const mode = this.incrementalMode();
    const modeLabel = mode ? 'incremental' : 'completo (full reload)';
    this.confirmAction.set({
      title: 'Preparar fuente GA03',
      message: `Esta acción cargará registros desde CSV hacia PocketBase hotel_reservation_events_03 en modo ${modeLabel}. No carga directo a MongoDB. ¿Desea continuar?`,
      handler: () => this.execAction(this.api.triggerSeed(this.targetPocketbase(), mode)),
    });
  }

  triggerClearEvidence() {
    this.confirmAction.set({
      title: 'Limpiar evidencia local GA03',
      message: 'Esta acción eliminará reportes, logs, .parquet, .jsonl y .json generados por el ETL GA03. Los datos en MongoDB se conservan y solo se sobrescriben al re-ejecutar el pipeline. No toca PocketBase. ¿Desea continuar?',
      handler: () => this.execAction(this.api.triggerClearEvidence()),
    });
  }

  triggerStop(process: string) {
    const label = process === 'seed' ? 'Preparación' : 'Pipeline';
    this.confirmAction.set({
      title: `Detener ${label}`,
      message: `Esta acción detendrá el proceso de ${label} GA03 en ejecución. ¿Desea continuar?`,
      handler: () => this.execAction(this.api.triggerStop(process)),
    });
  }

  toggleSection(key: string) {
    this.openSection.update(v => v === key ? null : key);
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

  serviceTone(tone: ServiceStatusCard['tone']): 'success' | 'warning' | 'danger' {
    return tone === 'muted' || tone === 'error' ? 'warning' : tone;
  }

  serviceLabel(tone: ServiceStatusCard['tone']): string {
    return tone === 'success' ? 'Disponible'
      : tone === 'warning' ? 'Atención'
      : tone === 'error' ? 'Error'
      : 'N/D';
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
