import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import type { ApiError } from '../../../../core/api/api-error.model';
import { catchAndToastError } from '../../../../shared/utils/catch-and-toast';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ManualReservationApiService } from '../../services/manual-reservation-api.service';
import type { HotelOption, RoomTypeOption } from '../../models/manual-reservation.model';

/** Custom validator: check-out must be after check-in */
function dateRangeValidator(c: AbstractControl): ValidationErrors | null {
  const checkIn = c.get('checkInDate')?.value;
  const checkOut = c.get('checkOutDate')?.value;
  if (!checkIn || !checkOut) return null;
  return checkOut > checkIn ? null : { dateRangeInvalid: 'La fecha de salida debe ser posterior a la fecha de entrada' };
}

@Component({
  selector: 'app-manual-reservation-new-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './manual-reservation-new-page.html',
  styleUrl: './manual-reservation-new-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManualReservationNewPageComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly manualApi = inject(ManualReservationApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly operationMode = inject(OperationModeService);

  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly errorMessage = signal('');
  readonly hotelOptions = signal<HotelOption[]>([]);
  readonly roomTypeOptions = signal<RoomTypeOption[]>([]);
  readonly roomTypesLoading = signal(false);



  readonly computedNights = computed(() => {
    const checkIn = this.form.controls.checkInDate.value;
    const checkOut = this.form.controls.checkOutDate.value;
    if (!checkIn || !checkOut) return 0;
    const inDate = new Date(checkIn);
    const outDate = new Date(checkOut);
    const diff = (outDate.getTime() - inDate.getTime()) / (1000 * 60 * 60 * 24);
    return diff > 0 ? diff : 0;
  });

  readonly today = new Date().toISOString().split('T')[0];

  // Templates for the hidden <input type="date"> trigger
  /** Obtener el mensaje de error del validador dateRange, necesario porque form.errors?.['key'] no compila en Angular 22 */
  get dateRangeError(): string | null {
    const err = this.form.errors?.['dateRangeInvalid'];
    return typeof err === 'string' ? err : null;
  }

  readonly triggerMap = {
    checkIn: { forId: 'date-checkin' },
    checkOut: { forId: 'date-checkout' },
  };

  readonly form = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]],
    roomTypeId: ['', [Validators.required]],
    guestName: ['', [Validators.required]],
    guestEmail: ['', [Validators.required, Validators.email]],
    guestPhone: [''],
    checkInDate: ['', [Validators.required]],
    checkOutDate: ['', [Validators.required]],
    adults: [2, [Validators.required, Validators.min(1), Validators.max(20)]],
    children: [0, [Validators.required, Validators.min(0), Validators.max(10)]],
    rooms: [1, [Validators.required, Validators.min(1), Validators.max(10)]],
    comment: [''],
  }, { validators: dateRangeValidator });

  constructor() {
    this.loadHotelOptions();
    // Watch hotel changes to reset dates
    this.form.controls.propId.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.form.controls.checkInDate.setValue('');
        this.form.controls.checkOutDate.setValue('');
        this.form.controls.roomTypeId.setValue('');
        this.roomTypeOptions.set([]);
      });
  }

  /** Open the native datepicker for the given field */
  triggerDatePicker(field: 'checkInDate' | 'checkOutDate') {
    const el = document.getElementById(field === 'checkInDate' ? 'date-checkin' : 'date-checkout') as HTMLInputElement | null;
    if (!el) return;
    try {
      el.showPicker();
    } catch {
      // Fallback: focus triggers native picker on mobile / older browsers
      el.focus();
    }
  }

  /** Format a YYYY-MM-DD string to dd/mm/aaaa */
  formatDate(value: string): string {
    if (!value) return '';
    const d = new Date(value + 'T00:00:00');
    return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  private loadHotelOptions() {
    this.loading.set(true);
    this.manualApi.getHotelOptions()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (options) => {
          this.hotelOptions.set(options);
          this.loading.set(false);
        },
        error: (err) => {
          // Dev visibility: log + toast so we know why the dropdown is empty.
          // The user-facing errorMessage is preserved for context below.
          catchAndToastError('manual.loadHotelOptions', undefined)(err);
          this.errorMessage.set('No se pudieron cargar los hoteles.');
          this.loading.set(false);
        }
      });
  }

  onHotelChange() {
    const propId = this.form.controls.propId.value;
    this.form.controls.roomTypeId.setValue('');
    this.roomTypeOptions.set([]);
    if (propId < 1) return;

    this.roomTypesLoading.set(true);
    this.manualApi.getRoomTypes(propId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (types) => {
          this.roomTypeOptions.set(types);
          this.roomTypesLoading.set(false);
        },
        error: (err) => {
          // Was silent — now visible in console + toast (loading flag still
          // flips correctly so the spinner stops).
          catchAndToastError('manual.loadRoomTypes', undefined)(err);
          this.roomTypesLoading.set(false);
        }
      });
  }

  adjustValue(field: 'adults' | 'children' | 'rooms', delta: number) {
    const control = this.form.controls[field];
    const newValue = control.value + delta;
    control.setValue(newValue);
    control.markAsDirty();
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');

    const v = this.form.getRawValue();
    this.manualApi.createManualReservation({
      propId: v.propId,
      roomTypeId: v.roomTypeId,
      guestName: v.guestName,
      guestEmail: v.guestEmail,
      guestPhone: v.guestPhone,
      checkInDate: v.checkInDate,
      checkOutDate: v.checkOutDate,
      adults: v.adults,
      children: v.children,
      rooms: v.rooms,
      comment: v.comment,
    }).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          void this.router.navigate(['/management/recepcion', result.bookingId]);
        },
        error: (err: ApiError) => {
          this.errorMessage.set(err.message || 'Error al crear la reserva manual.');
          this.submitting.set(false);
        }
      });
  }

  resetForm() {
    this.form.reset({
      propId: 0,
      roomTypeId: '',
      guestName: '',
      guestEmail: '',
      guestPhone: '',
      checkInDate: '',
      checkOutDate: '',
      adults: 2,
      children: 0,
      rooms: 1,
      comment: '',
    });
    this.roomTypeOptions.set([]);
    this.errorMessage.set('');
  }
}
