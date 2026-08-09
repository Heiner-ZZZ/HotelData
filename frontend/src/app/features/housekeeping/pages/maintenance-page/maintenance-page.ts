import { DecimalPipe, KeyValuePipe } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, computed, effect, inject, signal,
} from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { lastValueFrom, map, of } from 'rxjs';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ConfirmDialogComponent } from '../../../../shared/ui/confirm-dialog/confirm-dialog.component';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { HousekeepingSubNavComponent } from '../../components/housekeeping-sub-nav/housekeeping-sub-nav';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { HousekeepingApiService, type MaintenanceTaskItem, type RoomStatusItem } from '../../services/housekeeping-api.service';
import { PaginatedListResponse, normalizePaginatedList } from '../../utils/paginated-list-response';

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

/**
 * Status colors — delegated to design tokens
 * (`frontend/src/styles/_scss-variables.scss`). Status keys kept
 * verbatim so the template lookups (`statusColors[status]`) keep
 * working; only the value shifts from a hardcoded hex to a
 * `var(--token)` reference. Auto-adapts to the active theme via
 * `[data-theme="dark"]` overlay.
 */
const STATUS_COLORS: Record<string, string> = {
  scheduled: 'var(--accent)',
  in_progress: 'var(--warning)',
  inspection: 'var(--purple-strong)',
  completed: 'var(--success)',
};

const TASK_TYPE_LABELS: Record<string, string> = {
  preventive: 'Preventivo',
  corrective: 'Correctivo',
  inspection: 'Inspección',
};

interface MaintenanceQuery {
  propId: number;
  status: string | undefined;
  priority: string | undefined;
  page: number;
}

/** Helper: extract a runtime error message without `any`.
 *
 * Handles: `Error` instances, plain strings, and duck-typed objects with a
 * string `message` field (covers Angular's `HttpErrorResponse`, XHR errors,
 * and any other framework-neutrally typed error).
 */
function toErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  if (typeof err === 'object' && err !== null && 'message' in err) {
    const msg = (err as { message: unknown }).message;
    if (typeof msg === 'string') return msg;
  }
  return fallback;
}

@Component({
  selector: 'app-maintenance-page',
  imports: [
    DecimalPipe, KeyValuePipe, ReactiveFormsModule,
    PropertySelectorComponent, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent,
    HousekeepingSubNavComponent, ConfirmDialogComponent,
  ],
  templateUrl: './maintenance-page.html',
  styleUrl: './maintenance-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MaintenancePageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly fb = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly opMode = inject(OperationModeService);

  // ── Reactive URL params ──
  private readonly qp = toSignal(this.route.queryParamMap, { initialValue: this.route.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly statusFilter = computed(() => this.qp()?.get('status') ?? '');
  readonly priorityFilter = computed(() => this.qp()?.get('priority') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly selectedLabel = signal(this.route.snapshot.queryParamMap.get('prop_label') ?? '');

  // ── Room labels (for create form select) ──
  readonly roomItems = signal<RoomStatusItem[]>([]);

  // ── Maintenance resource ──
  readonly maintenanceResource = rxResource<PaginatedListResponse<MaintenanceTaskItem>, MaintenanceQuery | undefined>({
    params: () => {
      const pid = this.selectedPropId();
      if (!pid) return undefined;
      return {
        propId: pid,
        status: this.statusFilter() || undefined,
        priority: this.priorityFilter() || undefined,
        page: this.currentPage(),
      };
    },
    stream: ({ params }) => {
      if (params === undefined) return of<PaginatedListResponse<MaintenanceTaskItem>>({ items: [] });
      const { propId, status, priority, page } = params;
      return this.api.getMaintenance(propId, status, priority, page).pipe(
        map(normalizePaginatedList),
      );
    },
  });

  constructor() {
    // Side-channel: refresh `roomItems` whenever the selected property changes.
    // Hoisted out of `rxResource.stream()` so status/priority/page mutations do
    // NOT re-fire it, and replaced the nested `.subscribe()` calls with an
    // Angular 22 `effect()` that reads the propId signal directly. Cleanup is
    // implicit — the effect re-runs on each propId change and silently overwrites.
    effect(() => {
      const pid = this.selectedPropId();
      if (!pid) return;
      void this.refreshRoomItems(pid);
    });
  }

  /** Best-effort side-channel refresh for the room-select metadata. */
  private async refreshRoomItems(propId: number): Promise<void> {
    try {
      await lastValueFrom(this.api.syncRoomStatus(propId));
      const roomResp = await lastValueFrom(this.api.getRoomStatus(propId, undefined, 1));
      this.roomItems.set(roomResp.items);
    } catch {
      // Silent — the maintenance list still renders correctly without room metadata.
    }
  }

  readonly maintenanceData = computed<PaginatedListResponse<MaintenanceTaskItem>>(() => this.maintenanceResource.value() ?? { items: [] });

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
    const items: MaintenanceTaskItem[] = this.maintenanceData()?.items ?? [];
    return {
      scheduled: items.filter((i) => i.status === 'scheduled').length,
      inProgress: items.filter((i) => i.status === 'in_progress').length,
      inspection: items.filter((i) => i.status === 'inspection').length,
      completed: items.filter((i) => i.status === 'completed').length,
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
    roomId: ['', Validators.required],
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

  setPriorityFilter(priority: string): void {
    const next = priority === this.priorityFilter() ? '' : priority;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { priority: next || null, page: null },
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
      // Abrir el form de nuevo mantenimiento → modo insert en el nav.
      this.opMode.setMode('insert', 'Mantenimiento');
      this.createForm.reset({
        roomId: '',
        taskType: 'preventive',
        title: '',
        description: '',
        priority: 'normal',
        scheduledDate: todayLocalIso(),
        autoBlock: true,
        status: 'scheduled',
      });
    } else {
      this.opMode.reset();
    }
  }

  startEdit(item: MaintenanceTaskItem): void {
    this.showCreateForm.set(true);
    this.editingId.set(item.id);
    // Editar mantenimiento existente → modo update.
    this.opMode.setMode('update', `Mantenimiento — ${item.title}`);
    // Defer patchValue so select options render before value is set
    queueMicrotask(() => {
      // Normalize scheduledDate to datetime-local format (YYYY-MM-DDTHH:mm)
      let dt = todayLocalIso();
      if (item.scheduledDate) {
        const raw = item.scheduledDate;
        if (raw.includes('T')) {
          dt = raw.slice(0, 16);
        } else if (raw.length >= 10) {
          dt = raw.slice(0, 10) + 'T00:00';
        }
      }
      this.createForm.patchValue({
        roomId: item.roomId || '',
        taskType: item.taskType || 'preventive',
        title: item.title || '',
        description: item.description || '',
        priority: item.priority || 'normal',
        scheduledDate: dt,
        autoBlock: item.autoBlock ?? true,
        status: item.status || 'scheduled',
      });
    });
  }

  cancelForm(): void {
    this.opMode.reset();
    this.showCreateForm.set(false);
    this.editingId.set(null);
  }

  async submitTask(): Promise<void> {
    if (this.createForm.invalid) return;
    const val = this.createForm.getRawValue();
    const editId = this.editingId();
    const payload = {
      prop_id: this.selectedPropId() || 0,
      room_id: val.roomId,
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
      this.opMode.reset();
      this.maintenanceResource.reload();
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al guardar mantenimiento'));
      this.message.set('');
    }
  }

  // ── Quick actions ──
  async markInProgress(item: MaintenanceTaskItem): Promise<void> {
    const confirmed = await this.confirmDialog.open({
      title: 'Iniciar mantenimiento',
      message: `¿Iniciar el mantenimiento «${item.title}» en Hab. ${item.roomLabel}?`,
      variant: 'warning',
    });
    if (!confirmed) return;
    try {
      await lastValueFrom(this.api.updateMaintenance(item.id, {
        prop_id: item.propId,
        room_id: item.roomId,
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
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al iniciar mantenimiento'));
      this.message.set('');
    }
  }

  async markInspection(item: MaintenanceTaskItem): Promise<void> {
    const confirmed = await this.confirmDialog.open({
      title: 'Enviar a inspección',
      message: `¿Enviar «${item.title}» a inspección?`,
      variant: 'warning',
    });
    if (!confirmed) return;
    try {
      await lastValueFrom(this.api.updateMaintenance(item.id, {
        prop_id: item.propId,
        room_id: item.roomId,
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
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al enviar a inspección'));
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
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al completar mantenimiento'));
      this.message.set('');
    }
  }

  async classifyNoCost(item: MaintenanceTaskItem): Promise<void> {
    try {
      await lastValueFrom(this.api.reconcileNoCostMaintenance(item.id));
      this.message.set(`Sin costo registrado: ${item.title}`);
      this.errorMessage.set('');
      this.maintenanceResource.reload();
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'No se pudo clasificar el mantenimiento'));
      this.message.set('');
    }
  }

  canClassifyNoCost(item: MaintenanceTaskItem): boolean {
    return !item.actualCost
      && !item.expenseInvoiceId
      && !item.vendorId
      && item.financialLinkStatus !== 'no_cost_recorded';
  }

  async deleteMaintenanceItem(taskId: string, title: string): Promise<void> {
    const ok = await this.confirmDialog.open({
      title: 'Eliminar mantenimiento',
      message: `¿Eliminar la tarea de mantenimiento "${title}"?`,
      confirmLabel: 'Eliminar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: `Mantenimiento — ${title}`,
    });
    if (!ok) return;
    try {
      await lastValueFrom(this.api.deleteMaintenance(taskId));
      this.message.set('🗑️ Mantenimiento eliminado');
      this.errorMessage.set('');
      this.maintenanceResource.reload();
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al eliminar mantenimiento'));
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
