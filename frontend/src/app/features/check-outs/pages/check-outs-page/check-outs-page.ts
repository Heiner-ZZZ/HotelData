import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { CheckOutsViewModel } from '../../models/check-outs.model';
import { CheckOutsApiService } from '../../services/check-outs-api.service';

function todayIso(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

function shiftDate(iso: string, days: number): string {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

@Component({
  selector: 'app-check-outs-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule],
  templateUrl: './check-outs-page.html',
  styleUrl: './check-outs-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckOutsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(CheckOutsApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<CheckOutsViewModel | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly dateForm = this.formBuilder.nonNullable.group({
    operationDate: [todayIso(), [Validators.required]]
  });

  readonly selectedPropId = signal(0);
  readonly selectedPropName = signal('');
  readonly filter = signal('');
  readonly propertyOptions = signal<Array<{ propId: number; label: string }>>([]);
  readonly dropdownOpen = signal(false);

  readonly filteredOptions = computed(() => {
    const q = this.filter().toLowerCase().trim();
    const opts = this.propertyOptions();
    return q ? opts.filter(p => p.label.toLowerCase().includes(q)) : opts;
  });

  constructor() {
    this.route.queryParamMap.pipe(
      map((params) => ({
        propId: Number(params.get('prop_id') ?? '0'),
        operationDate: params.get('date') || todayIso()
      })),
      distinctUntilChanged((a, b) => a.propId === b.propId && a.operationDate === b.operationDate),
      switchMap(({ propId, operationDate }) => {
        this.viewState.set('loading');
        this.message.set('');
        this.errorMessage.set('');
        return this.api.getCheckOuts(operationDate, propId || undefined);
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (vm) => {
        this.viewModel.set(vm);
        this.dateForm.controls.operationDate.setValue(vm.operationDate, { emitEvent: false });
        this.propertyOptions.set(vm.propertyOptions);
        const selected = vm.propertyOptions.find(p => p.propId === vm.propId);
        this.selectedPropId.set(vm.propId ?? 0);
        this.selectedPropName.set(selected?.label || '');
        this.viewState.set(vm.items.length ? 'success' : 'empty');
      },
      error: () => this.viewState.set('error')
    });
  }

  navigateDate(days: number): void {
    const current = this.dateForm.controls.operationDate.value;
    this.dateForm.controls.operationDate.setValue(shiftDate(current, days));
    this.applyFilters();
  }

  goToday(): void {
    this.dateForm.controls.operationDate.setValue(todayIso());
    this.applyFilters();
  }

  applyFilters(): void {
    const date = this.dateForm.controls.operationDate.value;
    const propId = this.selectedPropId();
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null, date }
    });
  }

  selectProperty(propId: number, label: string): void {
    this.dropdownOpen.set(false);
    this.selectedPropId.set(propId);
    this.selectedPropName.set(label);
    if (propId) this.filter.set(label);
    else this.filter.set('');
    this.applyFilters();
  }

  clearProperty(): void {
    this.selectProperty(0, '');
  }

  toggleDropdown(): void {
    this.dropdownOpen.update(v => !v);
  }

  closeDropdown(): void {
    setTimeout(() => this.dropdownOpen.set(false), 200);
  }

  completeCheckOut(bookingId: string): void {
    const current = this.viewModel();
    if (!current) return;
    this.api.completeCheckOut(bookingId).pipe(
      switchMap(() => this.api.getCheckOuts(current.operationDate, current.propId || undefined)),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (vm) => {
        this.viewModel.set(vm);
        this.viewState.set(vm.items.length ? 'success' : 'empty');
        this.message.set('Check-out completado');
        this.errorMessage.set('');
      },
      error: (err: ApiError) => {
        this.errorMessage.set(err.message || 'Error al completar check-out.');
        this.message.set('');
      }
    });
  }
}
