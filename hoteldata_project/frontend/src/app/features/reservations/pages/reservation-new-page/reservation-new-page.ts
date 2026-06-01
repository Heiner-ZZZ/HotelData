import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import type { ApiError } from '../../../../core/api/api-error.model';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ReservationCreateInput, ReservationHotelOption } from '../../models/reservations.model';
import { ReservationsApiService } from '../../services/reservations-api.service';

@Component({
  selector: 'app-reservation-new-page',
  imports: [ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, RouterLink],
  templateUrl: './reservation-new-page.html',
  styleUrl: './reservation-new-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReservationNewPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly router = inject(Router);

  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly errorMessage = signal('');
  readonly hotelOptions = signal<ReservationHotelOption[]>([]);
  readonly selectedHotel = computed(() => {
    const selectedId = this.form.controls.propId.value;
    return this.hotelOptions().find((item) => item.propId === selectedId) || null;
  });

  readonly form = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]],
    guestName: ['', [Validators.required]],
    guestEmail: ['', [Validators.required, Validators.email]],
    checkInDate: ['', [Validators.required]],
    checkOutDate: ['', [Validators.required]],
    adults: [2, [Validators.required, Validators.min(1)]],
    children: [0, [Validators.required, Validators.min(0)]],
    rooms: [1, [Validators.required, Validators.min(1)]],
    comment: ['']
  });

  constructor() {
    const prefixedPropId = Number(this.activatedRoute.snapshot.queryParamMap.get('prop_id') ?? '0');
    this.reservationsApi
      .getOptions()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (options) => {
          this.hotelOptions.set(options);
          if (prefixedPropId > 0) {
            this.form.controls.propId.setValue(prefixedPropId);
          }
          this.loading.set(false);
        },
        error: () => {
          this.errorMessage.set('No fue posible cargar el formulario de reservas.');
          this.loading.set(false);
        }
      });
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');

    const value = this.form.getRawValue();
    const payload: ReservationCreateInput = {
      propId: value.propId,
      guestName: value.guestName,
      guestEmail: value.guestEmail,
      checkInDate: value.checkInDate,
      checkOutDate: value.checkOutDate,
      adults: value.adults,
      children: value.children,
      rooms: value.rooms,
      comment: value.comment
    };

    this.reservationsApi
      .createReservation(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          void this.router.navigate(['/reservations', result.bookingId]);
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible crear la reserva.');
          this.submitting.set(false);
        }
      });
  }
}
