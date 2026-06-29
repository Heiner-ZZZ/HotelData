import { DatePipe, KeyValuePipe } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, computed, inject, signal,
} from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { lastValueFrom } from 'rxjs';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { HousekeepingApiService, type MaintenanceTaskItem } from '../../services/housekeeping-api.service';

function todayLocalIso(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 16);
}

const STATUS_OPTIONS = ['scheduled', 'in_progress', 'inspection', 'completed'] as const;
const PRIORITIES = ['low', 'normal', 'high', 'urgent'] as const;

const STATUS_LABELS: Record<string, string> = {
  scheduled: 'Programado',
  in_progress: 'En Progreso',
  inspection: 'Inspección',
  completed: 'Completado',
};

const PRIORITY_LABELS: Record<string, string> = {
  low: 'Baja',
  normal: 'Normal',
  high: 'Alta',
  urgent: 'Urgente',
};

const STATUS_COLORS: Record<string, string> = {
  scheduled: '#1463ff',
  in_progress: '#d97706',
  inspection: '#7c3aed',
  completed: '#059669',
};

const TASK_TYPE_LABELS: Record<string, string> = {
  preventive: 'Preventivo',
  corrective: 'Correctivo',
  inspection: 'Inspección',
};

@Component({
  selector: 'app-maintenance-page',
  imports: [
    DatePipe, KeyValuePipe, ReactiveFormsModule,
    PropertySelectorComponent, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent,
  ],
  templateUrl: './maintenance-page.html',
  styleUrl: './maintenance-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MaintenancePageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly fb = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── Reactive URL params ──
  private readonly qp = toSignal(this.route.queryParamMap, { initialValue: this.route.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly statusFilter = computed(() => this.qp()?.get('status') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly selectedLabel = signal(this.route.snapshot.queryParamMap.get('prop_label') ?? '');

  // ── Room labels (for create form select) ──
  readonly roomLabels = signal<string[]>([]);

  // ── Maintenance resource ──
  readonly maintenanceResource = rxResource<any, any>({
    params: () => {
      const pid = this.selectedPropId();
      if (!pid) return undefined;
      return {
        propId: pid,
        status: this.statusFilter() || undefined,
        page: this.currentPage(),
      };
    },
    stream: ({ params }) => {
      const { propId, status, page } = params as any;

      // Sync rooms + fetch room labels (side effect via subscribe)
      this.api.syncRoomStatus(propId).subscribe({
        next: () => {
          this.api.getRoomStatus(propId, undefined, 1).subscribe({
            next: (roomData) => this.roomLabels.set(roomData.items.map(r => r.roomNumber || r.roomLabel)),
            error: () => {},
          });
        },
        error: () => {},
      });

      return this.api.getMaintenance(propId, status, page);
    },
  });

  readonly maintenanceData = computed(() => this.maintenanceResource.value() ?? null);

  readonly viewState = computed(() => {
    const r = this.maintenanceResource;
    if (r.isLoading() || r.status() === 'idle') return 'loading';
    if (r.error()) return 'error';
    const d = r.value();
    if (!d || !d.items.length) return 'empty';
    return 'success';
  });

  // ── Stats summary ──
  readonly statsSummary = computed(() => {
    const items = this.maintenanceData()?.items ?? [];
    return {
      scheduled: items.filter((i: any) => i.status === 'scheduled').length,
      inProgress: items.filter((i: any) => i.status === 'in_progress').length,
      inspection: items.filter((i: any) => i.status === 'inspection').length,
      completed: items.filter((i: any) => i.status === 'completed').length,
    };
  });

  // ── UI state ──
  readonly showCreateForm = signal(false);
  readonly editingId = signal<string | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  // ── Complete modal ──
  readonly showCompleteModal = signal(false);
  readonly completingItem = signal<MaintenanceTaskItem | null>(null);

  // ── Create/Edit Form ──
  readonly createForm = this.fb.nonNullable.group({
    roomLabel: ['', Validators.required],
    taskType: ['preventive'],
    title: ['', Validators.required],
    description: [''],
    priority: ['normal'],
    scheduledDate: [todayLocalIso()],
    autoBlock: [true],
    status: ['scheduled', Validators.required],
  });

  // ── Complete Form ──
  readonly completeForm = this.fb.nonNullable.group({
    observations: [''],
    unblockRoom: [true],
  });

  // ── Constants ──
  readonly statusOptions = [...STATUS_OPTIONS];
  readonly priorities = [...PRIORITIES];
  readonly statusLabels = STATUS_LABELS;
  readonly priorityLabels = PRIORITY_LABELS;
  readonly statusColors = STATUS_COLORS;
  readonly taskTypeLabels = TASK_TYPE_LABELS;

  // ── Property selection ──
  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, label);
    } else {
      this.propertyCtx.clear();
    }
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: label || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  // ── Filters ──
  setStatusFilter(status: string): void {
    const next = status === this.statusFilter() ? '' : status;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { status: next || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  // ── Pagination ──
  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: page > 1 ? page : null },
      queryParamsHandling: 'merge',
    });
  }

  // ── Create / Edit Form ──
  toggleCreateForm(): void {
    this.showCreateForm.update(v => !v);
    this.editingId.set(null);
    if (this.showCreateForm()) {
      this.createForm.reset({
        roomLabel: '',
        taskType: 'preventive',
        title: '',
        description: '',
        priority: 'normal',
        scheduledDate: todayLocalIso(),
        autoBlock: true,
        status: 'scheduled',
      });
    }
  }

  startEdit(item: MaintenanceTaskItem): void {
    this.editingId.set(item.id);
    this.showCreateForm.set(true);
    this.createForm.setValue({
      roomLabel: item.roomLabel,
      taskType: item.taskType,
      title: item.title,
      description: item.description || '',
      priority: item.priority,
      scheduledDate: item.scheduledDate ? item.scheduledDate.slice(0, 16) : todayLocalIso(),
      autoBlock: item.autoBlock,
      status: item.status || 'scheduled',
    });
  }

  cancelForm(): void {
    this.showCreateForm.set(false);
    this.editingId.set(null);
  }

  async submitTask(): Promise<void> {
    if (this.createForm.invalid) return;
    const val = this.createForm.getRawValue();
    const editId = this.editingId();
    const payload = {
      prop_id: this.selectedPropId() || 0,
      room_label: val.roomLabel,
      task_type: val.taskType,
      title: val.title,
      description: val.description || undefined,
      priority: val.priority,
      scheduled_date: val.scheduledDate || undefined,
      auto_block: val.autoBlock,
      status: val.status,
    };

    try {
      if (editId) {
        await lastValueFrom(this.api.updateMaintenance(editId, payload));
      } else {
        await lastValueFrom(this.api.createMaintenance(payload));
      }
      this.message.set(editId ? 'Mantenimiento actualizado' : 'Mantenimiento programado');
      this.errorMessage.set('');
      this.showCreateForm.set(false);
      this.editingId.set(null);
      this.maintenanceResource.reload();
    } catch (err: any) {
      this.errorMessage.set(err.message || 'Error al guardar mantenimiento');
      this.message.set('');
    }
  }

  // ── Quick actions ──
  async markInProgress(item: MaintenanceTaskItem): Promise<void> {
    try {
      await lastValueFrom(this.api.updateMaintenance(item.id, {
        prop_id: item.propId,
        room_label: item.roomLabel,
        task_type: item.taskType,
        title: item.title,
        description: item.description || undefined,
        priority: item.priority,
        scheduled_date: item.scheduledDate || undefined,
        auto_block: item.autoBlock,
        status: 'in_progress',
      }));
      this.message.set(`🔧 Mantenimiento iniciado — ${item.title}`);
      this.errorMessage.set('');
      this.maintenanceResource.reload();
    } catch (err: any) {
      this.errorMessage.set(err.message || 'Error al iniciar mantenimiento');
      this.message.set('');
    }
  }

  async markInspection(item: MaintenanceTaskItem): Promise<void> {
    try {
      await lastValueFrom(this.api.updateMaintenance(item.id, {
        prop_id: item.propId,
        room_label: item.roomLabel,
        task_type: item.taskType,
        title: item.title,
        description: item.description || undefined,
        priority: item.priority,
        scheduled_date: item.scheduledDate || undefined,
        auto_block: item.autoBlock,
        status: 'inspection',
      }));
      this.message.set(`🔍 ${item.title} enviado a inspección`);
      this.errorMessage.set('');
      this.maintenanceResource.reload();
    } catch (err: any) {
      this.errorMessage.set(err.message || 'Error al enviar a inspección');
      this.message.set('');
    }
  }

  // ── Complete Modal ──
  openCompleteModal(item: MaintenanceTaskItem): void {
    this.completingItem.set(item);
    this.completeForm.reset({ observations: '', unblockRoom: item.autoBlock });
    this.showCompleteModal.set(true);
  }

  closeCompleteModal(): void {
    this.showCompleteModal.set(false);
    this.completingItem.set(null);
  }

  async submitCompleteMaintenance(): Promise<void> {
    const item = this.completingItem();
    if (!item) return;
    const val = this.completeForm.getRawValue();

    try {
      await lastValueFrom(this.api.completeMaintenance(item.id, val.observations || ''));
      this.message.set(`✅ Mantenimiento completado — ${item.title}`);
      this.errorMessage.set('');
      this.closeCompleteModal();
      this.maintenanceResource.reload();
    } catch (err: any) {
      this.errorMessage.set(err.message || 'Error al completar mantenimiento');
      this.message.set('');
    }
  }

  async deleteMaintenanceItem(taskId: string): Promise<void> {
    try {
      await lastValueFrom(this.api.deleteMaintenance(taskId));
      this.message.set('🗑️ Mantenimiento eliminado');
      this.errorMessage.set('');
      this.maintenanceResource.reload();
    } catch (err: any) {
      this.errorMessage.set(err.message || 'Error al eliminar mantenimiento');
      this.message.set('');
    }
  }

  // ── Helpers ──
  formatDate(val: string): string {
    if (!val) return '—';
    const d = new Date(val);
    if (isNaN(d.getTime())) return val.slice(0, 10);
    return d.toLocaleDateString('es-MX', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  }

  statusClass(status: string): string {
    return `badge-${status}`;
  }

  priorityClass(p: string): string {
    return `prio-${p}`;
  }

  canStart(item: MaintenanceTaskItem): boolean { return item.status === 'scheduled'; }
  canInspect(item: MaintenanceTaskItem): boolean { return item.status === 'in_progress'; }
  canComplete(item: MaintenanceTaskItem): boolean { return item.status !== 'completed'; }
}
