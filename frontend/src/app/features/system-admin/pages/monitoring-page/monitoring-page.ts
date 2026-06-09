import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, inject, OnInit, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { MonitoringViewModel, ServiceStatusCard } from '../../models/monitoring.model';
import { MonitoringApiService } from '../../services/monitoring-api.service';
import type { Observable } from 'rxjs';
import type { ActionResponseDto } from '../../models/monitoring.dto';

@Component({
  selector: 'app-monitoring-page',
  imports: [
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './monitoring-page.html',
  styleUrl: './monitoring-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonitoringPageComponent implements OnInit {
  private readonly api = inject(MonitoringApiService);
  private readonly destroyRef = inject(DestroyRef);
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<MonitoringViewModel | null>(null);
  readonly loadErrorMessage = signal('');

  readonly actionMessage = signal('');
  readonly actionError = signal('');
  readonly actionBusy = signal(false);

  readonly selectedFile = signal<File | null>(null);
  readonly uploadBusy = signal(false);
  readonly targetRecords = signal(300000);
  readonly openSection = signal<string | null>(null);
  readonly confirmAction = signal<{ title: string; message: string; handler: () => void } | null>(null);
  readonly targetOptions = Array.from({ length: 16 }, (_, i) => {
    const val = (i + 1) * 100000;
    return { value: val, label: val.toLocaleString('es') };
  });

  readonly fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  ngOnInit() {
    this.destroyRef.onDestroy(() => this.stopPolling());
    this.loadData();
  }

  private startPolling() {
    this.stopPolling();
    this.pollTimer = setInterval(() => this.loadData(true), 1000);
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
        setTimeout(() => this.loadData(), 300);
      },
      error: (err: ApiError) => {
        this.uploadBusy.set(false);
        this.actionError.set(err.message || 'Error al subir el archivo.');
      },
    });
  }

  triggerValidate() {
    this.confirmAction.set({
      title: 'Validar dataset GA03',
      message: 'Esta acción verificará que PocketBase tenga los registros objetivo y que MongoDB esté disponible. No modifica datos. ¿Desea continuar?',
      handler: () => this.execAction(this.api.triggerValidate(this.targetRecords())),
    });
  }

  triggerRunPipeline() {
    this.confirmAction.set({
      title: 'Ejecutar pipeline GA03',
      message: 'Esta acción ejecutará el ETL principal PocketBase → JSONL → Parquet → MongoDB. Puede reemplazar la carga vigente en fact_hotel_reservations. ¿Desea continuar?',
      handler: () => this.execAction(this.api.triggerRunPipeline(this.targetRecords())),
    });
  }

  triggerSeed() {
    this.confirmAction.set({
      title: 'Preparar fuente GA03',
      message: 'Esta acción cargará registros desde CSV hacia PocketBase hotel_reservation_events_03. No carga directo a MongoDB. ¿Desea continuar?',
      handler: () => this.execAction(this.api.triggerSeed(this.targetRecords())),
    });
  }

  triggerClearEvidence() {
    this.confirmAction.set({
      title: 'Limpiar evidencia local GA03',
      message: 'Esta acción eliminará los reportes locales GA03 de progreso, validación, calidad, ejecución y log de preparación. No toca PocketBase ni MongoDB. ¿Desea continuar?',
      handler: () => this.execAction(this.api.triggerClearEvidence()),
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
    this.loadData();
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

  private loadData(isPoll = false) {
    if (!isPoll) {
      this.viewState.set('loading');
    }
    this.loadErrorMessage.set('');
    this.api
      .getMonitoringData()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set('success');
          if (vm.progress.preparationTarget > 0) {
            this.targetRecords.set(vm.progress.preparationTarget);
          }
          if (vm.progress.isRunning) {
            this.startPolling();
          } else {
            this.stopPolling();
          }
        },
        error: (error: ApiError) => {
          this.stopPolling();
          this.loadErrorMessage.set(error.message || 'No fue posible cargar el monitoreo.');
          this.viewState.set('error');
        },
      });
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
          setTimeout(() => this.loadData(), 500);
        } else {
          this.actionError.set(result.display_message + ' ' + (result.summary_output || ''));
        }
      },
      error: (err: ApiError) => {
        this.actionBusy.set(false);
        this.actionError.set(err.message || 'Error al ejecutar la acción.');
      },
    });
  }
}
