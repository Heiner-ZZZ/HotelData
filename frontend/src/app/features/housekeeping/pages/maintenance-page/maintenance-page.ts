import { SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingApiService, type MaintenanceTaskItem, type PaginatedResponse } from '../../services/housekeeping-api.service';

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

const PRIORITIES = ['low', 'normal', 'high', 'urgent'] as const;
const STATUS_OPTIONS = ['scheduled', 'in_progress', 'completed'] as const;

@Component({
  selector: 'app-maintenance-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, PropertySelectorComponent, ReactiveFormsModule, SlicePipe],

  templateUrl: './maintenance-page.html',
  styleUrl: './maintenance-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MaintenancePageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<PaginatedResponse<MaintenanceTaskItem> | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');
  readonly roomLabels = signal<string[]>([]);
  readonly showCreateForm = signal(false);
  readonly editingId = signal<string | null>(null);

  readonly statusFilter = signal<string>('');
  readonly createForm = this.formBuilder.nonNullable.group({
    roomLabel: ['', Validators.required],
    taskType: ['preventive'],
    title: ['', Validators.required],
    description: [''],
    priority: ['normal'],
    scheduledDate: [todayIso()],
  });

  readonly priorities = [...PRIORITIES];
  readonly statusOptions = [...STATUS_OPTIONS];

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          status: params.get('status') ?? '',
          propId: Number(params.get('prop_id') ?? '0'),
          propLabel: params.get('prop_label') ?? '',
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.status === b.status && a.propId === b.propId),
        switchMap(({ page, status, propId, propLabel }) => {
          this.viewState.set('loading');
          this.statusFilter.set(status);
          this.selectedPropId.set(propId);
          if (!propId) {
            this.propertyCtx.clear();
            this.roomLabels.set([]);
            return this.api.getMaintenance(undefined, status || undefined, page);
          }
          const label = propLabel || this.propertyCtx.currentPropLabel() || `Propiedad #${propId}`;
          this.selectedLabel.set(label);
          this.propertyCtx.setProperty(propId, label);
          return this.api.syncRoomStatus(propId).pipe(
            switchMap(() => this.api.getRoomStatus(propId, undefined, 1)),
            switchMap((roomData) => {
              this.roomLabels.set(roomData.items.map(r => r.roomNumber || r.roomLabel));
              this.selectedLabel.set(label);
              this.propertyCtx.setProperty(propId, label);
              return this.api.getMaintenance(propId, status || undefined, page);
            }),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  setStatusFilter(status: string): void {
    this.statusFilter.set(status === this.statusFilter() ? '' : status);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { status: this.statusFilter() || null, page: null },
    });
  }

  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: page > 1 ? page : null },
    });
  }

  toggleCreateForm(): void {
    this.showCreateForm.update((v) => !v);
    this.editingId.set(null);
    if (this.showCreateForm()) {
      this.createForm.reset({ roomLabel: '', taskType: 'preventive', title: '', description: '', priority: 'normal', scheduledDate: todayIso() });
    }
  }

  onPropSelected(event: { propId: number; label: string }): void {
    if (!event.propId) this.propertyCtx.clear();
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    this.propertyCtx.setProperty(event.propId, label);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: label || null },
    });
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
      scheduledDate: item.scheduledDate ? item.scheduledDate.slice(0, 10) : todayIso(),
    });
  }

  cancelForm(): void {
    this.showCreateForm.set(false);
    this.editingId.set(null);
  }

  submitTask(): void {
    if (this.createForm.invalid) return;
    const val = this.createForm.getRawValue();
    const editId = this.editingId();
    const obs = editId
      ? this.api.updateMaintenance(editId, {
          prop_id: this.selectedPropId() || 0,
          room_label: val.roomLabel,
          task_type: val.taskType,
          title: val.title,
          description: val.description || undefined,
          priority: val.priority,
          scheduled_date: val.scheduledDate || undefined,
        })
      : this.api.createMaintenance({
          prop_id: this.selectedPropId() || 0,
          room_label: val.roomLabel,
          task_type: val.taskType,
          title: val.title,
          description: val.description || undefined,
          priority: val.priority,
          scheduled_date: val.scheduledDate || undefined,
        });

    obs.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.message.set(editId ? 'Mantenimiento actualizado' : 'Mantenimiento programado exitosamente');
        this.errorMessage.set('');
        this.showCreateForm.set(false);
        this.editingId.set(null);
        this.refresh();
      },
      error: (err) => {
        this.errorMessage.set(err.message || 'Error al programar mantenimiento');
        this.message.set('');
      },
    });
  }

  completeTask(taskId: string): void {
    this.api
      .completeMaintenance(taskId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.message.set('Mantenimiento completado');
          this.errorMessage.set('');
          this.refresh();
        },
        error: (err) => {
          this.errorMessage.set(err.message || 'Error al completar mantenimiento');
          this.message.set('');
        },
      });
  }

  deleteMaintenanceItem(taskId: string): void {
    this.api
      .deleteMaintenance(taskId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.message.set('Mantenimiento eliminado');
          this.errorMessage.set('');
          this.refresh();
        },
        error: (err) => {
          this.errorMessage.set(err.message || 'Error al eliminar mantenimiento');
          this.message.set('');
        },
      });
  }

  private refresh(): void {
    const current = this.data();
    if (!current) return;
    this.viewState.set('loading');
    this.api
      .getMaintenance(this.selectedPropId() || undefined, this.statusFilter() || undefined, current.page)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }
}
