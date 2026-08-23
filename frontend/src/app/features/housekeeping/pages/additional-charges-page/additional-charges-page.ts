import { DatePipe, SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { InfoTooltipComponent } from '../../../../shared/ui/info-tooltip/info-tooltip.component';
import { AmountInputDirective } from '../../../../shared/ui/amount-input/amount-input.directive';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ConfirmDialogComponent } from '../../../../shared/ui/confirm-dialog/confirm-dialog.component';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingSubNavComponent } from '../../components/housekeeping-sub-nav/housekeeping-sub-nav';
import { HousekeepingApiService, type AdditionalChargeItem, type PaginatedResponse } from '../../services/housekeeping-api.service';
import { ReservationsApiService } from '../../../reservations/services/reservations-api.service';

@Component({
  selector: 'app-additional-charges-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PropertySelectorComponent, ReactiveFormsModule, DatePipe, SlicePipe, InfoTooltipComponent, AmountInputDirective, ConfirmDialogComponent, HousekeepingSubNavComponent],

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
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly opMode = inject(OperationModeService);

  readonly viewState = signal<ViewState | 'no-property'>('no-property');
  readonly data = signal<PaginatedResponse<AdditionalChargeItem> | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');
  readonly repairingId = signal<string | null>(null);

  readonly filterBookingId = signal('');
  readonly showCreateForm = signal(false);
  readonly editingId = signal<string | null>(null);
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
    chargeDate: [''],
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
    const amount = parseFloat(String(this.createForm.controls.amount.value)) || 0;
    const qty = this.createForm.controls.quantity.value || 1;
    return (amount * qty).toFixed(2);
  }

  toggleCreateForm(): void {
    this.showCreateForm.update((v) => !v);
    this.editingId.set(null);
    if (this.showCreateForm()) {
      // Abrir el form de nuevo cargo → modo insert en el nav.
      this.opMode.setMode('insert', 'Cargo');
      this.createForm.reset({ bookingId: '', concept: '', amount: '0.00' as any, quantity: 1, chargeDate: '', note: '' });
      this.selectedPropId.set(0);
      this.loadReservations();
    } else {
      this.opMode.reset();
    }
  }

  startEdit(item: AdditionalChargeItem): void {
    this.editingId.set(item.id);
    this.showCreateForm.set(true);
    // Editar cargo existente → modo update.
    this.opMode.setMode('update', `Cargo — ${item.concept}`);
    // Convert chargeDate ISO to datetime-local format
    let dt = '';
    if (item.chargeDate) {
      try {
        const d = new Date(item.chargeDate);
        if (!isNaN(d.getTime())) {
          const pad = (n: number) => String(n).padStart(2, '0');
          dt = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        }
      } catch { /* leave empty */ }
    }
    queueMicrotask(() => {
      this.createForm.patchValue({
        bookingId: item.bookingId || '',
        concept: item.concept || '',
        amount: parseFloat((item.amount || 0).toFixed(2)).toFixed(2) as any,
        quantity: item.quantity || 1,
        chargeDate: dt,
        note: item.note || '',
      });
    });
    // Load reservations so the select has options
    this.loadReservations();
    this.selectedPropId.set(item.propId || 0);
  }

  cancelForm(): void {
    this.opMode.reset();
    this.showCreateForm.set(false);
    this.editingId.set(null);
  }

  onReservationSelect(bookingId: string): void {
    const r = this.reservations().find(res => res.bookingId === bookingId);
    if (r) {
      this.selectedPropId.set(r.propId);
    }
  }

  submitCharge(): void {
    if (this.createForm.invalid) return;
    const raw = this.createForm.getRawValue();
    // Parse amount from string (could be "25.00" from blur or "25" from manual input)
    const amount = parseFloat(String(raw.amount)) || 0;
    const editId = this.editingId();

    if (editId) {
      // ── Update existing charge ──
      this.api
        .updateCharge(editId, {
          concept: raw.concept,
          amount,
          quantity: raw.quantity,
          charge_date: raw.chargeDate || undefined,
          note: raw.note || undefined,
        }, this.selectedPropId())
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.message.set('Cargo actualizado correctamente');
            this.errorMessage.set('');
            this.showCreateForm.set(false);
            this.editingId.set(null);
            this.opMode.reset();
            this.refresh();
          },
          error: (err) => {
            this.errorMessage.set(err.error?.detail || err.message || 'Error al actualizar cargo. Solo se pueden editar cargos del mismo día.');
            this.message.set('');
          },
        });
    } else {
      // ── Create new charge ──
      this.api
        .createCharge({
          booking_id: raw.bookingId,
          prop_id: this.selectedPropId(),
          concept: raw.concept,
          amount,
          quantity: raw.quantity,
          charge_date: raw.chargeDate || undefined,
          note: raw.note || undefined,
        })
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.message.set('Cargo registrado exitosamente');
            this.errorMessage.set('');
            this.showCreateForm.set(false);
            this.opMode.reset();
            this.refresh();
          },
          error: (err) => {
            this.errorMessage.set(err.message || 'Error al registrar cargo');
            this.message.set('');
          },
        });
    }
  }

  repairChargePosting(item: AdditionalChargeItem): void {
    if (item.postingStatus !== 'posting_failed' || this.repairingId()) return;
    this.repairingId.set(item.id);
    this.api.repairChargePosting(item.id, this.selectedPropId())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.message.set(`Cargo enlazado al folio ${item.folioNumber || ''} y publicado correctamente`);
          this.errorMessage.set('');
          this.repairingId.set(null);
          this.refresh();
        },
        error: (err) => {
          this.errorMessage.set(err.error?.detail || 'No se pudo enlazar el cargo al folio.');
          this.message.set('');
          this.repairingId.set(null);
        },
      });
  }

  async deleteChargeWithConfirm(item: AdditionalChargeItem): Promise<void> {
    const ok = await this.confirmDialog.open({
      title: 'Eliminar cargo',
      message: `¿Eliminar el cargo "${item.concept}" de la reserva ${item.bookingId.slice(0, 12)}...?`,
      details: [
        `Monto: $${item.total.toFixed(2)} USD`,
        'Se generará un ajuste de reversión en el folio del huésped.',
      ],
      confirmLabel: 'Eliminar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: `Cargo — ${item.concept}`,
    });
    if (!ok) return;

    this.api.deleteCharge(item.id, this.selectedPropId())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.message.set('Cargo eliminado y reversión aplicada al folio');
          this.errorMessage.set('');
          this.refresh();
        },
        error: (err) => {
          this.errorMessage.set(err.message || 'Error al eliminar cargo');
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
