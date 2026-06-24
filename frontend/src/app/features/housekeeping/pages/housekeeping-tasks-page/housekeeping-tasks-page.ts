import { SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingApiService, type HousekeepingTaskItem, type PaginatedResponse } from '../../services/housekeeping-api.service';

const TASK_TYPES = ['cleaning', 'deep_clean', 'turnover', 'inspection'] as const;
const PRIORITIES = ['low', 'normal', 'high', 'urgent'] as const;
const STATUS_OPTIONS = ['pending', 'completed'] as const;

@Component({
  selector: 'app-housekeeping-tasks-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, SlicePipe],

  templateUrl: './housekeeping-tasks-page.html',
  styleUrl: './housekeeping-tasks-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HousekeepingTasksPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<PaginatedResponse<HousekeepingTaskItem> | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');
  readonly showCreateForm = signal(false);

  readonly statusFilter = signal<string>('');
  readonly createForm = this.formBuilder.nonNullable.group({
    roomLabel: ['', Validators.required],
    taskType: ['cleaning', Validators.required],
    priority: ['normal'],
    assignedTo: [''],
    note: [''],
  });

  readonly taskTypes = [...TASK_TYPES];
  readonly priorities = [...PRIORITIES];
  readonly statusOptions = [...STATUS_OPTIONS];

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          status: params.get('status') ?? '',
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.status === b.status),
        switchMap(({ page, status }) => {
          this.viewState.set('loading');
          this.statusFilter.set(status);
          return this.api.getTasks(undefined, status || undefined, undefined, page);
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
    if (this.showCreateForm()) {
      this.createForm.reset({ roomLabel: '', taskType: 'cleaning', priority: 'normal', assignedTo: '', note: '' });
    }
  }

  submitTask(): void {
    if (this.createForm.invalid) return;
    const val = this.createForm.getRawValue();
    this.api
      .createTask({
        prop_id: 0,
        room_label: val.roomLabel,
        task_type: val.taskType,
        assigned_to: val.assignedTo || undefined,
        priority: val.priority,
        note: val.note || undefined,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.message.set('Tarea creada exitosamente');
          this.errorMessage.set('');
          this.showCreateForm.set(false);
          this.refresh();
        },
        error: (err) => {
          this.errorMessage.set(err.message || 'Error al crear tarea');
          this.message.set('');
        },
      });
  }

  completeTask(taskId: string): void {
    this.api
      .completeTask(taskId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.message.set('Tarea completada');
          this.errorMessage.set('');
          this.refresh();
        },
        error: (err) => {
          this.errorMessage.set(err.message || 'Error al completar tarea');
          this.message.set('');
        },
      });
  }

  private refresh(): void {
    const current = this.data();
    if (!current) return;
    this.viewState.set('loading');
    this.api
      .getTasks(undefined, this.statusFilter() || undefined, undefined, current.page)
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
