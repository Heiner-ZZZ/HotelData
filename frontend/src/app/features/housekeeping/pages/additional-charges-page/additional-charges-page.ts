import { SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingSubNavComponent } from '../../components/housekeeping-sub-nav/housekeeping-sub-nav';
import { HousekeepingApiService, type AdditionalChargeItem, type PaginatedResponse } from '../../services/housekeeping-api.service';
import { ReservationsApiService } from '../../../reservations/services/reservations-api.service';

@Component({
  selector: 'app-additional-charges-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PropertySelectorComponent, ReactiveFormsModule, SlicePipe, HousekeepingSubNavComponent],

  templateUrl: './additional-charges-page.html',
  styleUrl: './additional-charges-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdditionalChargesPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);

  readonly viewState = signal<ViewState | 'no-property'>('no-property');
  readonly data = signal<PaginatedResponse<AdditionalChargeItem> | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly filterBookingId = signal('');
  readonly showCreateForm = signal(false);
  readonly propId = signal(0);
  readonly propLabel = signal('');

  readonly reservations = signal<{ bookingId: string; guestName: string; propId: number; status: string }[]>([]);
  readonly reservationsLoading = signal(false);
  readonly selectedPropId = signal(0);

  readonly createForm = this.formBuilder.nonNullable.group({
    bookingId: ['', Validators.required],
    concept: ['', Validators.required],
    amount: [0, [Validators.required, Validators.min(0.01)]],
    quantity: [1, [Validators.required, Validators.min(1)]],
    note: [''],
  });

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          bookingId: params.get('booking_id') ?? '',
          propId: Number(params.get('prop_id') ?? '0'),
          propLabel: params.get('prop_label') ?? '',
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.bookingId === b.bookingId && a.propId === b.propId),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(({ page, bookingId, propId, propLabel }) => {
        this.propId.set(propId);
        this.propLabel.set(propLabel);
        this.filterBookingId.set(bookingId);
        if (!propId) {
          this.viewState.set('no-property');
          return;
        }
        this.viewState.set('loading');
        this.api.getCharges(bookingId || undefined, propId, page)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: (data) => {
              this.data.set(data);
              this.viewState.set(data.items.length ? 'success' : 'empty');
            },
            error: () => this.viewState.set('error'),
          });
      });

    /** Sync property context */
    effect(() => {
      const pid = this.propId();
      if (pid) {
        this.propertyCtx.setProperty(pid, this.propLabel() || `Propiedad #${pid}`);
      } else {
        this.propertyCtx.clear();
      }
    });
  }

  get totalFormatted(): string {
    const amount = this.createForm.controls.amount.value || 0;
    const qty = this.createForm.controls.quantity.value || 1;
    return (amount * qty).toFixed(2);
  }

  toggleCreateForm(): void {
    this.showCreateForm.update((v) => !v);
    if (this.showCreateForm()) {
      this.createForm.reset({ bookingId: '', concept: '', amount: 0, quantity: 1, note: '' });
      this.selectedPropId.set(0);
      this.loadReservations();
    }
  }

  onReservationSelect(bookingId: string): void {
    const r = this.reservations().find(res => res.bookingId === bookingId);
    if (r) {
      this.selectedPropId.set(r.propId);
    }
  }

  submitCharge(): void {
    if (this.createForm.invalid) return;
    const val = this.createForm.getRawValue();
    this.api
      .createCharge({
        booking_id: val.bookingId,
        prop_id: this.selectedPropId(),
        concept: val.concept,
        amount: val.amount,
        quantity: val.quantity,
        note: val.note || undefined,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.message.set('Cargo registrado exitosamente');
          this.errorMessage.set('');
          this.showCreateForm.set(false);
          this.refresh();
        },
        error: (err) => {
          this.errorMessage.set(err.message || 'Error al registrar cargo');
          this.message.set('');
        },
      });
  }

  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: page > 1 ? page : null },
      queryParamsHandling: 'merge',
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        prop_id: event.propId || null,
        prop_label: label || null,
        page: null,
      },
    });
  }

  private refresh(): void {
    const current = this.data();
    if (!current) return;
    const pid = this.propId();
    if (!pid) {
      this.viewState.set('no-property');
      return;
    }
    this.viewState.set('loading');
    this.api
      .getCharges(this.filterBookingId() || undefined, pid, current.page)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  private loadReservations(): void {
    this.reservationsLoading.set(true);
    this.reservationsApi.getReservations(1)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.reservations.set(
            res.items.map((r: any) => ({
              bookingId: r.bookingId,
              guestName: r.guestName || r.guest_name || 'Sin nombre',
              propId: r.propId || r.prop_id || 0,
              status: r.status,
            }))
          );
          this.reservationsLoading.set(false);
        },
        error: () => {
          this.reservationsLoading.set(false);
        },
      });
  }
}
