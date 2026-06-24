import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import type { ApiError } from '../../../../core/api/api-error.model';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ReservationCreateInput, ReservationHotelOption, ReservationPreview } from '../../models/reservations.model';
import { ReservationsApiService } from '../../services/reservations-api.service';

@Component({
  selector: 'app-reservation-new-page',
  imports: [CurrencyPipe, DatePipe, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, RouterLink],
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
  readonly previewing = signal(false);
  readonly errorMessage = signal('');
  readonly hotelOptions = signal<ReservationHotelOption[]>([]);
  readonly preview = signal<ReservationPreview | null>(null);
  readonly step = signal<'details' | 'review'>('details');

  /** Guest autocomplete: cached recent guests from sessionStorage */
  readonly guestSuggestions = signal<Array<{ name: string; email: string; phone: string }>>([]);
  readonly showGuestDropdown = signal(false);
  readonly guestSearchFocused = signal(false);

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
    guestPhone: [''],
    checkInDate: ['', [Validators.required]],
    checkOutDate: ['', [Validators.required]],
    adults: [2, [Validators.required, Validators.min(1), Validators.max(20)]],
    children: [0, [Validators.required, Validators.min(0), Validators.max(10)]],
    rooms: [1, [Validators.required, Validators.min(1), Validators.max(10)]],
    comment: ['']
  });

  constructor() {
    const prefixedPropId = Number(this.activatedRoute.snapshot.queryParamMap.get('prop_id') ?? '0');
    this._loadGuestSuggestions();
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
    this.loadPreview();
  }

  private loadPreview() {
    const payload = this.buildPayload();
    this.previewing.set(true);
    this.preview.set(null);
    this.reservationsApi
      .previewReservation(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.preview.set(result);
          this.previewing.set(false);
        },
        error: () => {
          this.previewing.set(false);
        }
      });
  }

  backToDetails() {
    this.step.set('details');
  }

  private buildPayload(): ReservationCreateInput {
    const v = this.form.getRawValue();
    return {
      propId: v.propId,
      guestName: v.guestName,
      guestEmail: v.guestEmail,
      guestPhone: v.guestPhone,
      checkInDate: v.checkInDate,
      checkOutDate: v.checkOutDate,
      adults: v.adults,
      children: v.children,
      rooms: v.rooms,
      comment: v.comment
    };
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    // Save guest data for future autocomplete
    const v = this.form.getRawValue();
    this._saveGuestSuggestion(v.guestName, v.guestEmail, v.guestPhone);

    this.submitting.set(true);
    this.errorMessage.set('');

    const payload = this.buildPayload();

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

  /** Load recently used guests from localStorage for autocomplete suggestions */
  private _loadGuestSuggestions() {
    try {
      const raw = localStorage.getItem('hoteldata_recent_guests');
      if (raw) {
        this.guestSuggestions.set(JSON.parse(raw));
      }
    } catch {
      // ignore corrupt localStorage
    }
  }

  /** Save a guest to localStorage for future autocomplete */
  private _saveGuestSuggestion(name: string, email: string, phone: string) {
    if (!name || !email) return;
    const current = this.guestSuggestions();
    const filtered = current.filter(g => g.email !== email);
    const updated = [{ name, email, phone }, ...filtered].slice(0, 10);
    this.guestSuggestions.set(updated);
    try {
      localStorage.setItem('hoteldata_recent_guests', JSON.stringify(updated));
    } catch {
      // localStorage full or unavailable
    }
  }

  /** Filter guest suggestions based on user input */
  readonly filteredGuestSuggestions = computed(() => {
    const query = this.form.controls.guestName.value.toLowerCase().trim();
    if (!query || query.length < 1) return this.guestSuggestions();
    return this.guestSuggestions().filter(
      g => g.name.toLowerCase().includes(query) || g.email.toLowerCase().includes(query)
    );
  });

  /** Select a guest from the autocomplete dropdown, filling name + email + phone */
  selectGuest(guest: { name: string; email: string; phone: string }) {
    this.form.controls.guestName.setValue(guest.name);
    this.form.controls.guestEmail.setValue(guest.email);
    this.form.controls.guestPhone.setValue(guest.phone || '');
    this.showGuestDropdown.set(false);
  }

  /** Toggle guest dropdown visibility */
  toggleGuestDropdown(show: boolean) {
    // Small delay to allow click events on dropdown items
    setTimeout(() => {
      if (!show && !this.guestSearchFocused()) return;
      this.showGuestDropdown.set(show);
    }, 150);
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
