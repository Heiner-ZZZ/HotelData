import { DatePipe } from '@angular/common';
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
  imports: [DatePipe, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, RouterLink],
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
  readonly step = signal<'details' | 'review'>('details');

  readonly selectedHotel = computed(() => {
    const selectedId = this.form.controls.propId.value;
    return this.hotelOptions().find((item) => item.propId === selectedId) || null;
  });

  readonly computedNights = computed(() => {
    const checkIn = this.form.controls.checkInDate.value;
    const checkOut = this.form.controls.checkOutDate.value;
    if (!checkIn || !checkOut) return 0;
    const inDate = new Date(checkIn);
    const outDate = new Date(checkOut);
    const diff = (outDate.getTime() - inDate.getTime()) / (1000 * 60 * 60 * 24);
    return diff > 0 ? diff : 0;
  });

  readonly roomSummary = computed(() => {
    const adults = this.form.controls.adults.value;
    const children = this.form.controls.children.value;
    const rooms = this.form.controls.rooms.value;
    const nights = this.computedNights();
    return { adults, children, rooms, nights };
  });

  readonly today = new Date().toISOString().split('T')[0];

  readonly form = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]],
    guestName: ['', [Validators.required]],
    guestEmail: ['', [Validators.required, Validators.email]],
    checkInDate: ['', [Validators.required]],
    checkOutDate: ['', [Validators.required]],
    adults: [2, [Validators.required, Validators.min(1), Validators.max(20)]],
    children: [0, [Validators.required, Validators.min(0), Validators.max(10)]],
    rooms: [1, [Validators.required, Validators.min(1), Validators.max(10)]],
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

  goToReview() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.step.set('review');
  }

  backToDetails() {
    this.step.set('details');
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
          void this.router.navigate(['..', result.bookingId], { relativeTo: this.activatedRoute });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible crear la reserva.');
          this.submitting.set(false);
        }
      });
  }

  adjustValue(field: 'adults' | 'children' | 'rooms', delta: number) {
    const control = this.form.controls[field];
    const newValue = control.value + delta;
    control.setValue(newValue);
    control.markAsDirty();
  }

  trackByPropId(_index: number, item: ReservationHotelOption): number {
    return item.propId;
  }
}
