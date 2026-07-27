import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { lastValueFrom, map, of, switchMap } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';
import { SlicePipe } from '@angular/common';


import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ConfirmDialogComponent } from '../../../../shared/ui/confirm-dialog/confirm-dialog.component';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { HousekeepingSubNavComponent } from '../../components/housekeeping-sub-nav/housekeeping-sub-nav';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { InfoTooltipComponent } from '../../../../shared/ui/info-tooltip/info-tooltip.component';
import { HousekeepingApiService, type HousekeepingTaskItem, type RoomStatusItem, type StaffUser } from '../../services/housekeeping-api.service';
import { PaginatedListResponse, normalizePaginatedList } from '../../utils/paginated-list-response';
import { roleLabel } from '../../../../core/auth/role-labels';

function todayLocalIso(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 16);
}

const TASK_TYPES = ['cleaning', 'deep_clean', 'turnover', 'inspection'] as const;
const PRIORITIES = ['low', 'normal', 'high', 'urgent'] as const;
const STATUS_OPTIONS = ['pending', 'in_progress', 'inspection', 'completed'] as const;

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendiente',
  in_progress: 'En Progreso',
  inspection: 'Inspección',
  completed: 'Completada',
};

const PRIORITY_LABELS: Record<string, string> = {
  low: 'Baja',
  normal: 'Normal',
  high: 'Alta',
  urgent: 'Urgente',
};

const TASK_TYPE_ICONS: Record<string, string> = {
  cleaning: 'cleaning_services',
  deep_clean: 'auto_awesome',
  turnover: 'sync',
  inspection: 'visibility',
};

const TASK_TYPE_LABELS: Record<string, string> = {
  cleaning: 'Limpieza',
  deep_clean: 'Limpieza profunda',
  turnover: 'Rotación',
  inspection: 'Inspección',
};

/** Concrete response shapes — replaces `rxResource<any, any>`. */
interface RoomListResponse {
  items: RoomStatusItem[];
}
interface StaffListResponse {
  staff: StaffUser[];
}
interface TasksQuery {
  propId: number;
  status: string | undefined;
  assignedTo: string | undefined;
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
  selector: 'app-housekeeping-tasks-page',
  imports: [
    EmptyStateComponent, ErrorStateComponent, LoadingStateComponent,
    PropertySelectorComponent, ReactiveFormsModule, SlicePipe, HousekeepingSubNavComponent,
    ConfirmDialogComponent, InfoTooltipComponent,
  ],
  templateUrl: './housekeeping-tasks-page.html',
  styleUrl: './housekeeping-tasks-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HousekeepingTasksPageComponent {
  // ── DI ──
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly fb = inject(FormBuilder);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── URL-driven state (toSignal auto-cleans, no DestroyRef) ──
  private readonly qp = toSignal(this.route.queryParamMap, { initialValue: this.route.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly statusFilter = computed(() => this.qp()?.get('status') ?? '');
  readonly assignedToFilter = computed(() => this.qp()?.get('assigned_to') ?? '');
  readonly priorityFilter = computed(() => this.qp()?.get('priority') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly selectedLabel = signal(this.route.snapshot.queryParamMap.get('prop_label') ?? '');

  // ── Derived ──
  readonly activeFilterCount = computed(() =>
    (this.statusFilter() ? 1 : 0) + (this.assignedToFilter() ? 1 : 0) + (this.priorityFilter() ? 1 : 0),
  );

  // ── Rooms resource (fetches room labels after sync) ──
  readonly roomsResource = rxResource<RoomListResponse, number | undefined>({
    params: () => this.selectedPropId() || undefined,
    stream: ({ params }) => {
      if (params === undefined) return of<RoomListResponse>({ items: [] });
      return this.api.syncRoomStatus(params).pipe(
        switchMap(() => this.api.getRoomStatus(params, undefined, 1)),
      );
    },
  });

  readonly roomItems = computed<RoomStatusItem[]>(() =>
    (this.roomsResource.value()?.items ?? []),
  );

  // ── Tasks resource ──
  readonly tasksResource = rxResource<PaginatedListResponse<HousekeepingTaskItem>, TasksQuery | undefined>({
    params: () => {
      const pid = this.selectedPropId();
      if (!pid) return undefined;
      return {
        propId: pid,
        status: this.statusFilter() || undefined,
        assignedTo: this.assignedToFilter() || undefined,
        priority: this.priorityFilter() || undefined,
        page: this.currentPage(),
      };
    },
    stream: ({ params }) => {
      if (params === undefined) return of<PaginatedListResponse<HousekeepingTaskItem>>({ items: [] });
      const { propId, status, assignedTo, priority, page } = params;
      return this.api.getTasks(propId, status, assignedTo, priority, page).pipe(
        map(normalizePaginatedList),
      );
    },
  });

  readonly tasks = computed<PaginatedListResponse<HousekeepingTaskItem>>(() => this.tasksResource.value() ?? { items: [] });

  readonly viewState = computed(() => {
    const r = this.tasksResource;
    if (r.isLoading()) return 'loading';
    if (r.error()) return 'error';
    if (!r.value()?.items.length) return 'empty';
    return 'success';
  });

  // ── Stats summary ──
  readonly statsSummary = computed(() => {
    const items: HousekeepingTaskItem[] = this.tasksResource.value()?.items ?? [];
    return {
      pending: items.filter((i) => i.status === 'pending').length,
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
  readonly completingItem = signal<HousekeepingTaskItem | null>(null);

  // ── Create / Edit Form ──
  readonly createForm = this.fb.nonNullable.group({
    roomId: ['', Validators.required],
    taskType: ['cleaning', Validators.required],
    priority: ['normal'],
    assignedTo: [''],
    note: [''],
    scheduledDate: [todayLocalIso()],
    status: ['pending', Validators.required],
  });

  // ── Complete Cleaning Form ──
  readonly completeForm = this.fb.nonNullable.group({
    observations: [''],
    damageFound: [false],
    damageDescription: [''],
    lostObjectFound: [false],
    lostObjectDescription: [''],
    needsMaintenance: [false],
    maintenanceDescription: [''],
  });

  // ── Display constants ──
  readonly taskTypes = [...TASK_TYPES];
  readonly priorities = [...PRIORITIES];
  readonly statusOptions = [...STATUS_OPTIONS];
  readonly statusLabels = STATUS_LABELS;
  readonly priorityLabels = PRIORITY_LABELS;
  readonly taskTypeIcons = TASK_TYPE_ICONS;
  readonly taskTypeLabels = TASK_TYPE_LABELS;
  readonly roleLabel = roleLabel;
  // ── Staff resource (real users instead of hardcoded) ──
  readonly staffResource = rxResource<StaffListResponse, number | undefined>({
    params: () => this.selectedPropId() || undefined,
    stream: ({ params }) => {
      if (params === undefined) return of<StaffListResponse>({ staff: [] });
      return this.api.getStaff(params);
    },
  });

  readonly staffUsers = computed<StaffUser[]>(() =>
    this.staffResource.value()?.staff ?? [],
  );

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

  // ── Filter actions ──
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

  onAssignedToChange(value: string): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { assigned_to: value || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  clearAllFilters(): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { status: null, assigned_to: null, priority: null, page: null },
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

  // ── Form actions (Create/Edit) ──
  toggleCreateForm(): void {
    this.showCreateForm.update(v => !v);
    this.editingId.set(null);
    if (this.showCreateForm()) {
      this.createForm.reset({
        roomId: '',
        taskType: 'cleaning',
        priority: 'normal',
        assignedTo: '',
        note: '',
        scheduledDate: todayLocalIso(),
        status: 'pending',
      });
    }
  }

  startEdit(item: HousekeepingTaskItem): void {
    this.showCreateForm.set(true);
    this.editingId.set(item.id);
    // Defer patchValue so select options render before value is set
    queueMicrotask(() => {
    // Map scheduledDate to datetime-local format (YYYY-MM-DDTHH:mm)
    let dt = todayLocalIso();
    if (item.scheduledDate) {
      try {
        const d = new Date(item.scheduledDate);
        if (!isNaN(d.getTime())) {
          const pad = (n: number) => String(n).padStart(2, '0');
          dt = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        }
      } catch { /* fallback to todayLocalIso */ }
    }
    this.createForm.patchValue({
      roomId: item.roomId || '',
      taskType: item.taskType || 'cleaning',
      priority: item.priority || 'normal',
      assignedTo: item.assignedTo || '',
      note: item.note || '',
      scheduledDate: dt,
      status: item.status || 'pending',
    });
    }); // end queueMicrotask
  }

  /** Get display name for a room option. */
  displayRoom(r: RoomStatusItem): string {
    const num = r.roomNumber || r.roomLabel;
    const type = r.roomTypeId ? ` (${r.roomTypeId})` : '';
    return `${num}${type}`;
  }

  /** Get display name for a staff user. */
  displayStaff(u: StaffUser): string {
    return u.display_name || u.username;
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
      room_id: val.roomId,
      task_type: val.taskType,
      assigned_to: val.assignedTo || undefined,
      priority: val.priority,
      note: val.note || undefined,
      scheduled_date: val.scheduledDate || undefined,
      status: val.status,
    };

    try {
      if (editId) {
        await lastValueFrom(this.api.updateTask(editId, payload));
      } else {
        await lastValueFrom(this.api.createTask(payload));
      }
      this.message.set(editId ? 'Tarea actualizada' : 'Tarea creada');
      this.errorMessage.set('');
      this.showCreateForm.set(false);
      this.editingId.set(null);
      this.tasksResource.reload();
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al guardar tarea'));
      this.message.set('');
    }
  }

  // ── Complete Cleaning Modal ──

  openCompleteModal(item: HousekeepingTaskItem): void {
    this.completingItem.set(item);
    this.completeForm.reset({
      observations: '',
      damageFound: false,
      damageDescription: '',
      lostObjectFound: false,
      lostObjectDescription: '',
      needsMaintenance: false,
      maintenanceDescription: '',
    });
    this.showCompleteModal.set(true);
  }

  closeCompleteModal(): void {
    this.showCompleteModal.set(false);
    this.completingItem.set(null);
  }

  async submitCompleteCleaning(): Promise<void> {
    const item = this.completingItem();
    if (!item) return;

    const val = this.completeForm.getRawValue();
    try {
      await lastValueFrom(this.api.completeCleaning({
        prop_id: item.propId,
        room_label: item.roomLabel,
        assigned_to: item.assignedTo || '',
        observations: val.observations || '',
        damage_found: val.damageFound,
        damage_description: val.damageDescription || '',
        lost_object_found: val.lostObjectFound,
        lost_object_description: val.lostObjectDescription || '',
        needs_maintenance: val.needsMaintenance,
        maintenance_description: val.maintenanceDescription || '',
      }));
      this.message.set(`✅ Limpieza completada — Hab. ${item.roomLabel}`);
      this.errorMessage.set('');
      this.closeCompleteModal();
      this.tasksResource.reload();
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al completar limpieza'));
      this.message.set('');
    }
  }

  // ── Quick actions ──

  async startCleaning(item: HousekeepingTaskItem): Promise<void> {
    const confirmed = await this.confirmDialog.open({
      title: 'Iniciar limpieza',
      message: `¿Iniciar limpieza en Hab. ${item.roomLabel}?`,
      details: [`Tarea: ${this.taskTypeLabels[item.taskType] || item.taskType}`, `Asignado: ${item.assignedTo || 'Sin asignar'}`],
      variant: 'warning',
    });
    if (!confirmed) return;
    try {
      await lastValueFrom(this.api.startCleaning(item.propId, item.roomLabel, item.assignedTo || 'system'));
      this.message.set(`🧹 Limpieza iniciada — Hab. ${item.roomLabel}`);
      this.errorMessage.set('');
      this.tasksResource.reload();
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al iniciar limpieza'));
      this.message.set('');
    }
  }

  async markInspection(item: HousekeepingTaskItem): Promise<void> {
    const confirmed = await this.confirmDialog.open({
      title: 'Enviar a inspección',
      message: `¿Enviar la tarea de Hab. ${item.roomLabel} a inspección?`,
      variant: 'warning',
    });
    if (!confirmed) return;
    try {
      await lastValueFrom(this.api.updateTask(item.id, {
        prop_id: item.propId,
        room_id: item.roomId,
        task_type: item.taskType,
        assigned_to: item.assignedTo || undefined,
        priority: item.priority,
        note: item.note || undefined,
        scheduled_date: item.scheduledDate || undefined,
        status: 'inspection',
      }));
      this.message.set('🔍 Tarea enviada a inspección');
      this.errorMessage.set('');
      this.tasksResource.reload();
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al enviar a inspección'));
      this.message.set('');
    }
  }

  async completeTask(taskId: string): Promise<void> {
    try {
      await lastValueFrom(this.api.completeTask(taskId));
      this.message.set('✅ Tarea completada');
      this.errorMessage.set('');
      this.tasksResource.reload();
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al completar tarea'));
      this.message.set('');
    }
  }

  async deleteTaskWithConfirm(taskId: string, roomLabel: string): Promise<void> {
    const ok = await this.confirmDialog.open({
      title: 'Eliminar tarea',
      message: `¿Eliminar la tarea de "Hab. ${roomLabel}"?`,
      confirmLabel: 'Eliminar',
      variant: 'danger',
    });
    if (ok) this.deleteTask(taskId);
  }

  async deleteTask(taskId: string): Promise<void> {
    try {
      await lastValueFrom(this.api.deleteTask(taskId));
      this.message.set('🗑️ Tarea eliminada');
      this.errorMessage.set('');
      this.tasksResource.reload();
    } catch (err: unknown) {
      this.errorMessage.set(toErrorMessage(err, 'Error al eliminar tarea'));
      this.message.set('');
    }
  }

  // ── Helpers ──

  formatDate(val: string): string {
    if (!val) return '--';
    const d = new Date(val);
    if (isNaN(d.getTime())) return val.replace('T', ' ').slice(0, 16);
    return d.toLocaleDateString('es-MX', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    });
  }

  statusClass(status: string): string {
    return (
      { pending: 'badge-pending', in_progress: 'badge-progress', inspection: 'badge-inspection', completed: 'badge-done' }[status]
    ) || 'badge-pending';
  }

  priorityClass(p: string): string { return `prio-${p}`; }
  canStartCleaning(item: HousekeepingTaskItem): boolean { return item.status === 'pending'; }
  canMarkInspection(item: HousekeepingTaskItem): boolean { return item.status === 'pending' || item.status === 'in_progress'; }
  canComplete(item: HousekeepingTaskItem): boolean { return item.status === 'pending' || item.status === 'in_progress' || item.status === 'inspection'; }
}
