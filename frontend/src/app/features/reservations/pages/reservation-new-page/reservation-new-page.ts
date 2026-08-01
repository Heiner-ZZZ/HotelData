import { CurrencyPipe } from '@angular/common';
import { httpResource, HttpParams } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal, ViewEncapsulation } from '@angular/core';
import type { AbstractControl, ValidationErrors } from '@angular/forms';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, EMPTY, switchMap, debounceTime } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { AuthService } from '../../../../core/auth/auth.service';
import { ReservationsAuthService } from '../../services/reservations-auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { RnPlannerSectionComponent } from './partials/rn-planner-section';
import { RnGuestSectionComponent } from './partials/rn-guest-section';
import { RnReviewSectionComponent } from './partials/rn-review-section';
import { mapReservationOptions } from '../../mappers/reservations.mapper';
import type { RatePlanOption, ReservationCreateInput, ReservationHotelOption, ReservationPreview } from '../../models/reservations.model';
import type { ReservationOptionsDto } from '../../models/reservations.dto';
import { ReservationsApiService } from '../../services/reservations-api.service';
import { GuestAmenityService } from '../../../amenities/services/guest-amenity.service';
import type { GuestAmenityCategoryDto } from '../../../amenities/models/guest-amenity.dto';

/**
 * Raw shape returned by `GET /reservations/rate-plans` — the route returns
 * `rate_plans: Array<RatePlanRaw>` and we map it to typed
 * `RatePlanOption[]` via `parse` (mirrors the optionsResource pattern).
 */
interface RatePlanRaw {
  rate_plan_id: string;
  name: string;
  description: string;
  base_rate: number;
  currency: string;
  is_active: boolean;
  avg_rate_per_night: number;
  total_price: number;
  nights: number;
}
interface RatePlansResponseDto {
  rate_plans?: RatePlanRaw[];
}

function validateStayDates(control: AbstractControl): ValidationErrors | null {
  const checkIn = String(control.get('checkInDate')?.value || '');
  const checkOut = String(control.get('checkOutDate')?.value || '');
  if (!checkIn || !checkOut) return null;
  return checkOut > checkIn ? null : { invalidStayDates: true };
}

function mapRatePlans(raw: RatePlansResponseDto): RatePlanOption[] {
  return (raw.rate_plans || []).map((p) => ({
    ratePlanId: p.rate_plan_id,
    name: p.name,
    description: p.description,
    baseRate: p.base_rate,
    currency: p.currency,
    isActive: p.is_active,
    avgRatePerNight: p.avg_rate_per_night,
    totalPrice: p.total_price,
    nights: p.nights,
  }));
}

@Component({
  selector: 'app-reservation-new-page',
  imports: [ReactiveFormsModule, RouterLink, CurrencyPipe,
    RnPlannerSectionComponent, RnGuestSectionComponent, RnReviewSectionComponent],
  templateUrl: './reservation-new-page.html',
  styleUrl: './reservation-new-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class ReservationNewPageComponent {
  // ─── Injections ───
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly reservationsAuth = inject(ReservationsAuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);
  private readonly guestAmenityService = inject(GuestAmenityService);

  // ─── Form ─── (declared BEFORE the toSignal fields that read it)
  readonly form = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]],
    guestName: ['', [Validators.required]],
    guestEmail: ['', [Validators.required, Validators.email]],
    guestPhone: ['', [Validators.required]],
    checkInDate: ['', [Validators.required]],
    checkOutDate: ['', [Validators.required]],
    // Standard overnight booking requires both arrival and departure times.
    // These are editable defaults, and the backend checks the hotel's policy.
    checkInTime: ['15:00', [Validators.required]],
    checkOutTime: ['12:00', [Validators.required]],
    adults: [2, [Validators.required, Validators.min(1), Validators.max(20)]],
    children: [0, [Validators.required, Validators.min(0), Validators.max(10)]],
    rooms: [1, [Validators.required, Validators.min(1), Validators.max(10)]],
    comment: [''],
    couponCode: [''],
    specialRequests: [[] as string[]],
    cedula: ['', [Validators.required]],
  }, { validators: validateStayDates });

  // ─── Form-driven signal sources that httpResource declarations read in their URL formula ───
  // httpResource re-fires automatically whenever any signal read inside its request fn changes.
  // This replaces the four manual `form.controls.X.valueChanges.subscribe(...)` chains that
  // used to live in the constructor — reactivity is now declarative, not imperative.
  private readonly propIdSignal = toSignal(this.form.controls.propId.valueChanges, {
    initialValue: this.form.controls.propId.value,
  });
  private readonly checkInDateSignal = toSignal(this.form.controls.checkInDate.valueChanges, {
    initialValue: this.form.controls.checkInDate.value,
  });
  private readonly checkOutDateSignal = toSignal(this.form.controls.checkOutDate.valueChanges, {
    initialValue: this.form.controls.checkOutDate.value,
  });

  // ─── httpResource declarations (GETs only — POSTs stay as `subscribe(takeUntilDestroyed)`) ───

  /** Hotel options dropdown — fired once on mount, no dependency. */
  readonly optionsResource = httpResource<ReservationHotelOption[]>(
    () => ({ url: '/reservations/options' }),
    { parse: (dto) => mapReservationOptions(dto as ReservationOptionsDto) },
  );

  /** Per-hotel availability — re-fires when propId or any date signal changes. */
  readonly availabilityResource = httpResource<{
    hasInventory: boolean;
    hasRoomTypes: boolean;
    totalRooms: number;
    availableRooms: number;
    message: string;
  }>(() => {
    const propId = this.propIdSignal();
    const checkIn = this.checkInDateSignal();
    const checkOut = this.checkOutDateSignal();
    if (!propId || !checkIn || !checkOut) return undefined;
    return {
      url: '/reservations/availability-check',
      method: 'GET' as const,
      params: new HttpParams()
        .set('prop_id', String(propId))
        .set('check_in', checkIn)
        .set('check_out', checkOut),
    };
  });

  /** Available rate plans for the selected hotel + dates + optional room type. */
  readonly ratePlansResource = httpResource<RatePlanOption[]>(() => {
    const propId = this.propIdSignal();
    const checkIn = this.checkInDateSignal();
    const checkOut = this.checkOutDateSignal();
    if (!propId || !checkIn || !checkOut) return undefined;
    let params = new HttpParams()
      .set('prop_id', String(propId))
      .set('check_in', checkIn)
      .set('check_out', checkOut);
    const roomTypeId = this.preselectedRoomTypeId();
    if (roomTypeId) {
      params = params.set('room_type_id', roomTypeId);
    }
    return { url: '/reservations/rate-plans', method: 'GET' as const, params };
  }, { parse: (dto) => mapRatePlans(dto as RatePlansResponseDto) });

  /** Amenity catalog per hotel — re-fires when propId changes. */
  readonly amenityResource = httpResource<{ catalog: GuestAmenityCategoryDto[] }>(() => {
    const propId = this.propIdSignal();
    if (!propId) return undefined;
    return {
      url: '/amenities/guest/catalog/by-prop',
      method: 'GET' as const,
      params: new HttpParams().set('prop_id', String(propId)),
    };
  });

  // ─── Writable signals preserved for template compatibility ───
  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly previewing = signal(false);
  readonly processingPayment = signal(false);
  readonly paymentError = signal('');
  readonly paymentResult = signal<{transactionId: string; cardLast4: string; cardBrand: string; authCode: string} | null>(null);
  readonly errorMessage = signal('');
  readonly hotelOptions = signal<ReservationHotelOption[]>([]);
  readonly preview = signal<ReservationPreview | null>(null);
  readonly step = signal<'details' | 'review' | 'payment'>('details');

  /** Room type ID and name passed from hotel detail page via query params */
  readonly preselectedRoomTypeId = signal('');
  readonly preselectedRoomTypeName = signal('');

  /** Availability status per hotel (legacy dict — kept so the existing template + helper still work). */
  readonly hotelAvailabilityStatus = signal<Record<number, 'unknown' | 'has_inventory' | 'no_inventory' | 'checking' | 'no_room_types'>>({});

  readonly guestSuggestions = signal<{ name: string; email: string; phone: string }[]>([]);
  readonly apiUserResults = signal<{ name: string; email: string; phone: string; cedula: string }[]>([]);
  readonly apiSearching = signal(false);
  readonly showGuestDropdown = signal(false);
  readonly guestSearchFocused = signal(false);

  /**
   * Bump-friendly signal that drives the debounced user-search pipeline.
   * Replaces the legacy ``Subject<string>`` pattern: the template (or the
   * guest-section partial) calls ``onUserSearchInput(value)`` which sets the
   * signal; ``toObservable()`` below re-evaluates through debounceTime → API
   * search users. The signal-based shape removes the Subject dependency from
   * the constructor and keeps the API consistent across the file.
   */
  readonly userSearchTrigger = signal('');

  readonly couponStatus = signal<{valid: boolean; message: string; discountPercent: number} | null>(null);
  readonly couponValidating = signal(false);

  readonly amenityCatalog = signal<GuestAmenityCategoryDto[]>([]);
  readonly amenityCatalogLoading = signal(false);
  readonly selectedAmenities = signal<Set<string>>(new Set());
  readonly amenityCatalogError = signal('');

  readonly availableRatePlans = signal<RatePlanOption[]>([]);
  readonly ratePlansLoading = signal(false);
  readonly selectedRatePlanId = signal('');

  readonly isStaff = this.reservationsAuth.isStaff;
  readonly isClient = this.reservationsAuth.isClient;

  readonly selectedHotel = computed(() => {
    const selectedId = this.propIdSignal();
    return this.hotelOptions().find((item) => item.propId === selectedId) || null;
  });

  readonly computedNights = computed(() => {
    const checkIn = this.checkInDateSignal();
    const checkOut = this.checkOutDateSignal();
    if (!checkIn || !checkOut) return 0;
    const inDate = new Date(checkIn);
    const outDate = new Date(checkOut);
    const diff = Math.round((outDate.getTime() - inDate.getTime()) / (1000 * 60 * 60 * 24));
    return diff > 0 ? diff : 0;
  });

  readonly roomSummary = computed(() => {
    const adults = this.form.controls.adults.value;
    const children = this.form.controls.children.value;
    const rooms = this.form.controls.rooms.value;
    const nights = this.computedNights();
    return { adults, children, rooms, nights };
  });

  /** Availability label and icon for a given hotel (legacy API consumed by `rn-planner-section`). */
  getHotelAvailabilityInfo(propId: number): { label: string; icon: string; color: string } | null {
    const status = this.hotelAvailabilityStatus()[propId];
    if (!status || status === 'unknown') return null;
    switch (status) {
      case 'checking': return { label: 'Verificando...', icon: 'sync', color: 'var(--muted-text)' };
      case 'has_inventory': return { label: 'Disponible', icon: 'check_circle', color: 'var(--success)' };
      case 'no_inventory': return { label: 'Sin disponibilidad', icon: 'error', color: 'var(--danger)' };
      case 'no_room_types': return { label: 'Sin tipos de habitación', icon: 'warning', color: 'var(--warning)' };
      default: return null;
    }
  }

  readonly specialRequestOptions = [
    { value: 'Cama extra', label: 'Cama extra' },
    { value: 'Cuna para bebé', label: 'Cuna para bebé' },
    { value: 'Accesibilidad (silla de ruedas)', label: 'Accesibilidad' },
    { value: 'Mascotas (Pet friendly)', label: 'Pet friendly' },
    { value: 'Piso alto', label: 'Piso alto' },
    { value: 'Llegada tarde', label: 'Llegada tarde' },
  ];

  readonly today = new Date().toISOString().split('T')[0];

  constructor() {
    const prefixedPropId = Number(this.activatedRoute.snapshot.queryParamMap.get('prop_id') ?? '0');
    const prefixedRoomType = this.activatedRoute.snapshot.queryParamMap.get('room_type') ?? '';
    const prefixedRoomTypeName = this.activatedRoute.snapshot.queryParamMap.get('room_type_name') ?? '';
    if (prefixedRoomType) {
      this.preselectedRoomTypeId.set(prefixedRoomType);
      this.preselectedRoomTypeName.set(prefixedRoomTypeName);
    }
    this._loadGuestSuggestions();
    this._restoreGuestDraft();
    this._persistGuestDraft();

    // ── Resources → writable signals (effect-based) ──

    // optionsResource.value() → hotelOptions + (initial) propId setValue + loading toggle.
    // The setValue triggers propIdSignal → amenityResource / availabilityResource / ratePlansResource
    // auto-fire on the same micro-task, so we don't need manual `checkHotelAvailability()` calls.
    effect(() => {
      const r = this.optionsResource.value();
      if (!r) return;
      this.hotelOptions.set(r);
      if (prefixedPropId > 0 && this.form.controls.propId.value === 0) {
        this.form.controls.propId.setValue(prefixedPropId);
      }
      this.loading.set(false);
    });

    // optionsResource.error() → toast + loading toggle (avoids the page getting stuck on loading=true).
    effect(() => {
      const err = this.optionsResource.error();
      if (!err) return;
      // The HTTP interceptor emits the single global toast for this failure.
      this.loading.set(false);
    });

    // availabilityResource.value() → hotelAvailabilityStatus dict.
    effect(() => {
      const r = this.availabilityResource.value();
      const propId = this.propIdSignal();
      if (!r || !propId) return;
      const status = r.hasRoomTypes
        ? (r.hasInventory ? 'has_inventory' : 'no_inventory')
        : 'no_room_types';
      this.hotelAvailabilityStatus.update(s => ({ ...s, [propId]: status }));
    });

    // ratePlansResource.value() → availableRatePlans + auto-select first plan.
    // The parse callback (`mapRatePlans`) already maps DTO → view-model.
    effect(() => {
      const plans = this.ratePlansResource.value();
      if (!plans) return;
      this.availableRatePlans.set(plans);
      if (plans.length > 0 && !this.selectedRatePlanId()) {
        this.selectedRatePlanId.set(plans[0].ratePlanId);
      }
    });

    // ratePlansResource.isLoading() → ratePlansLoading toggle (separate effect so transitions
    // catch even when the URL formula computes to undefined → IDLE → no value change).
    effect(() => {
      this.ratePlansLoading.set(this.ratePlansResource.isLoading());
    });

    // amenityResource.value() → amenityCatalog (success).
    effect(() => {
      const r = this.amenityResource.value();
      if (!r) return;
      this.amenityCatalog.set(r.catalog || []);
      this.amenityCatalogLoading.set(false);
    });

    // amenityResource.error() → empty catalog + error string + loading toggle (failure).
    effect(() => {
      const err = this.amenityResource.error();
      if (!err) return;
      this.amenityCatalog.set([]);
      this.amenityCatalogLoading.set(false);
      this.amenityCatalogError.set('No se pudo cargar el catálogo de amenities.');
    });

    // Reset selectedAmenities whenever the hotel changes (side-effect that has no home in an httpResource).
    // This used to be inline inside the propId valueChanges subscribe; preserved verbatim here.
    effect(() => {
      this.propIdSignal();
      this.selectedAmenities.set(new Set());
    });

    // ── Search registered users on the backend when staff types (debounced, rxjs-native) ──
    // httpResource has no native debounce: keeping `toObservable + debounceTime + distinctUntilChanged +
    // switchMap` is the canonical pattern for search-typeahead input. The signal-driven trigger
    // (`userSearchTrigger.set(value)`) keeps the input API fully reactive.
    toObservable(this.userSearchTrigger)
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((q) => {
          if (!q || q.length < 2) {
            this.apiUserResults.set([]);
            this.apiSearching.set(false);
            return EMPTY;
          }
          this.apiSearching.set(true);
          return this.reservationsApi.searchUsers(q).pipe(
            takeUntilDestroyed(this.destroyRef)
          );
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (result) => {
          if (result && 'items' in result) {
            this.apiUserResults.set(result.items);
          }
          this.apiSearching.set(false);
        },
        error: () => {
          this.apiUserResults.set([]);
          this.apiSearching.set(false);
        },
      });

    // Auto-fill guest data from user profile for client role
    if (this.isClient()) {
      const user = this.authService.currentUser();
      if (user) {
        this.form.controls.guestName.setValue(user.displayName || '');
        this.form.controls.guestEmail.setValue(user.email || '');
      }
    }
  }

  // ─── Payment form fields ───
  readonly cardNumber = signal('');
  readonly cardHolder = signal('');
  readonly cardExpiry = signal('');
  readonly cardCvv = signal('');
  readonly cardBrand = signal('');

  /** Detect card brand from first digits for real-time UI feedback */
  readonly detectedCardBrand = computed(() => {
    const n = this.cardNumber().replace(/\s/g, '');
    if (n.startsWith('4')) return 'Visa';
    if (/^5[1-5]/.test(n) || (n.length >= 4 && /^2[2-7]/.test(n))) return 'Mastercard';
    if (/^3[47]/.test(n)) return 'American Express';
    if (/^6011|^65/.test(n) || (n.length >= 3 && n.startsWith('64') && n[2] >= '4' && n[2] <= '9')) return 'Discover';
    return '';
  });

  /** Format card number with spaces every 4 digits */
  formatCardNumber(raw: string) {
    const digits = raw.replace(/\D/g, '').slice(0, 16);
    this.cardNumber.set(digits.replace(/(.{4})/g, '$1 ').trim());
  }

  /** Format expiry as MM/YY */
  formatExpiry(raw: string) {
    const digits = raw.replace(/\D/g, '').slice(0, 4);
    if (digits.length >= 2) {
      this.cardExpiry.set(digits.slice(0, 2) + '/' + digits.slice(2));
    } else {
      this.cardExpiry.set(digits);
    }
  }

  goToReview() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.toast.warning('Completa los campos obligatorios y selecciona fechas válidas para continuar.');
      return;
    }
    this.step.set('review');
    this.loadPreview();
  }

  goToPayment() {
    this.paymentError.set('');
    this.step.set('payment');
  }

  processPayment() {
    const cardNum = this.cardNumber().replace(/\s/g, '');
    const holder = this.cardHolder().trim();
    const exp = this.cardExpiry().trim();
    const cvv = this.cardCvv().trim();

    if (!cardNum || !holder || !exp || !cvv) {
      this.paymentError.set('Todos los campos de la tarjeta son requeridos.');
      return;
    }

    const amount = this.preview()?.totalPrice ?? 0;

    this.processingPayment.set(true);
    this.paymentError.set('');

    this.reservationsApi.processPayment({
      card_number: cardNum,
      card_holder: holder,
      expiry: exp,
      cvv: cvv,
      amount: amount,
    }).subscribe({
      next: (result) => {
        this.paymentResult.set({
          transactionId: result.transaction_id,
          cardLast4: result.card_last4,
          cardBrand: result.card_brand,
          authCode: result.auth_code,
        });
        this.processingPayment.set(false);
        // Auto-submit after successful payment
        this.submitWithPayment(result.transaction_id, result.card_last4);
      },
      error: (err) => {
        this.paymentError.set(err?.error?.detail || 'Error al procesar el pago. Verifica los datos.');
        this.processingPayment.set(false);
      },
    });
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

  /** Select a rate plan */
  selectRatePlan(planId: string): void {
    this.selectedRatePlanId.set(planId);
  }

  /** Get the currently selected rate plan */
  readonly selectedRatePlan = computed(() => {
    const id = this.selectedRatePlanId();
    return this.availableRatePlans().find(p => p.ratePlanId === id) || null;
  });

  toggleAmenity(label: string) {
    const current = new Set(this.selectedAmenities());
    if (current.has(label)) {
      current.delete(label);
    } else {
      current.add(label);
    }
    this.selectedAmenities.set(current);
  }

  private buildPayload(): ReservationCreateInput {
    const v = this.form.getRawValue();
    return {
      propId: v.propId,
      guestName: v.guestName,
      guestEmail: v.guestEmail,
      guestPhone: v.guestPhone,
      cedula: v.cedula,
      checkInDate: v.checkInDate,
      checkOutDate: v.checkOutDate,
      checkInTime: v.checkInTime || undefined,
      checkOutTime: v.checkOutTime || undefined,
      adults: v.adults,
      children: v.children,
      rooms: v.rooms,
      comment: v.comment,
      couponCode: v.couponCode,
      specialRequests: v.specialRequests,
      selectedAmenities: [...this.selectedAmenities()],
      roomTypeId: this.preselectedRoomTypeId() || undefined,
      ratePlanId: this.selectedRatePlanId() || undefined,
    };
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const previewData = this.preview();
    if (previewData && !previewData.available) {
      this.toast.error('No hay habitaciones disponibles para las fechas seleccionadas.');
      this.step.set('details');
      return;
    }
    // If there's a price > 0 OR deposit is required, go to payment step
    if ((previewData?.totalPrice ?? 0) > 0 || previewData?.depositRequired) {
      this.goToPayment();
      return;
    }
    this.submitWithPayment('', '');
  }

  private submitWithPayment(transactionId: string, cardLast4: string) {
    const v = this.form.getRawValue();
    this._saveGuestSuggestion(v.guestName, v.guestEmail, v.guestPhone);

    this.submitting.set(true);
    this.errorMessage.set('');

    const payload = this.buildPayload();
    payload.transactionId = transactionId;
    payload.paymentMethod = transactionId ? 'credit_card' : '';
    payload.cardLast4 = cardLast4;

    this.reservationsApi
      .createReservation(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          void this.router.navigate(['../confirmed', result.bookingId], { relativeTo: this.activatedRoute });
        },
        error: (error: ApiError) => {
          const msg = error.message || '';
          // The HTTP interceptor already presents the single global toast.
          this.errorMessage.set(msg || 'No fue posible crear la reserva.');
          this.submitting.set(false);
        }
      });
  }

  /** Load recently used guests from localStorage for autocomplete suggestions */
  private _loadGuestSuggestions() {
    try {
      const raw = localStorage.getItem('hoteldata_recent_guests');
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return;
      this.guestSuggestions.set(parsed.filter((guest): guest is { name: string; email: string; phone: string } =>
        !!guest && typeof guest.name === 'string' && typeof guest.email === 'string'
      ).map(guest => ({
        name: guest.name,
        email: guest.email,
        phone: typeof guest.phone === 'string' ? guest.phone : '',
      })));
    } catch {
      // Ignore corrupt or unavailable localStorage.
    }
  }

  private _restoreGuestDraft() {
    try {
      const raw = localStorage.getItem('hoteldata_booking_guest_draft');
      if (!raw) return;
      const draft = JSON.parse(raw) as Partial<{ guestName: string; guestEmail: string; guestPhone: string }>;
      this.form.patchValue({
        guestName: draft.guestName || '',
        guestEmail: draft.guestEmail || '',
        guestPhone: draft.guestPhone || '',
      }, { emitEvent: false });
    } catch {
      // Ignore corrupt or unavailable localStorage.
    }
  }

  private _persistGuestDraft() {
    this.form.valueChanges
      .pipe(debounceTime(250), takeUntilDestroyed(this.destroyRef))
      .subscribe(value => {
        try {
          localStorage.setItem('hoteldata_booking_guest_draft', JSON.stringify({
            guestName: value.guestName || '',
            guestEmail: value.guestEmail || '',
            guestPhone: value.guestPhone || '',
          }));
        } catch {
          // Browser storage can be disabled or full; booking still works.
        }
      });
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

  /** Combined guest suggestions: localStorage recent guests + API search results */
  readonly filteredGuestSuggestions = computed(() => {
    this.userSearchTrigger();
    const query = this.form.controls.guestName.value.toLowerCase().trim();
    const localGuests = this.guestSuggestions();
    const apiGuests = this.apiUserResults();

    // Show only recent guests when no query
    if (!query || query.length < 1) {
      return localGuests.map(g => ({ ...g, source: 'local' as const }));
    }

    // Merge: API results shown first, then matching localStorage entries (filter out dupes by email)
    const apiEmails = new Set(apiGuests.map(g => g.email.toLowerCase()));
    const merged: { name: string; email: string; phone: string; cedula?: string; source: 'api' | 'local' }[] = [
      ...apiGuests.map(g => ({ ...g, source: 'api' as const })),
      ...localGuests
        .filter(g => !apiEmails.has(g.email.toLowerCase()))
        .filter(g => g.name.toLowerCase().includes(query) || g.email.toLowerCase().includes(query))
        .map(g => ({ ...g, source: 'local' as const })),
    ];

    return merged;
  });

  /** Select a guest from the autocomplete dropdown, filling name + email + phone + cedula */
  selectGuest(guest: { name: string; email: string; phone: string; cedula?: string }) {
    this.form.controls.guestName.setValue(guest.name);
    this.form.controls.guestEmail.setValue(guest.email);
    this.form.controls.guestPhone.setValue(guest.phone || '');
    this.form.controls.cedula.setValue(guest.cedula || '');
    this.showGuestDropdown.set(false);
    this.guestSearchFocused.set(false);
  }

  /**
   * Push a guest-name keystroke into the debounced search pipeline.
   * Called from ``rn-guest-section`` (or the template directly) instead of
   * ``this.userSearch$.next(value)`` — the signal API keeps callers free of
   * any rxjs Subject import.
   */
  onUserSearchInput(value: string): void {
    this.userSearchTrigger.set(value);
  }

  toggleGuestDropdown(show: boolean) {
    if (show) {
      this.guestSearchFocused.set(true);
      this.showGuestDropdown.set(true);
      return;
    }
    this.guestSearchFocused.set(false);
    // Keep the list open briefly so a click on a suggestion is not swallowed.
    setTimeout(() => this.showGuestDropdown.set(false), 150);
  }

  /** Wrapper for rn-planner-section adjust output — casts string to union type */
  handleAdjust(data: { field: string; delta: number }) {
    const field = data.field as 'adults' | 'children' | 'rooms';
    const control = this.form.controls[field];
    const newValue = control.value + data.delta;
    control.setValue(newValue);
    control.markAsDirty();
  }

  trackByPropId(_index: number, item: ReservationHotelOption): number {
    return item.propId;
  }

  validateCoupon() {
    const code = this.form.controls.couponCode.value;
    const propId = this.form.controls.propId.value;
    if (!code) {
      this.couponStatus.set(null);
      return;
    }
    if (!propId) {
      this.couponStatus.set({valid: false, message: 'Selecciona un hotel primero', discountPercent: 0});
      return;
    }
    this.couponValidating.set(true);
    this.reservationsApi.validateCoupon(code, propId).subscribe({
      next: (res) => {
         this.couponStatus.set({
           valid: res.valid,
           message: res.message,
           discountPercent: res.discount_percent
         });
         this.couponValidating.set(false);
      },
      error: () => {
         this.couponStatus.set({valid: false, message: 'Error de validación', discountPercent: 0});
         this.couponValidating.set(false);
      }
    });
  }

  /** Wrapper for the rn-guest-section partial output format */
  handleToggleRequest(data: { request: string; checked: boolean }) {
    this._updateSpecialRequest(data.request, data.checked);
  }

  private _updateSpecialRequest(request: string, isChecked: boolean) {
    const current = this.form.controls.specialRequests.value;
    if (isChecked && !current.includes(request)) {
      this.form.controls.specialRequests.setValue([...current, request]);
    } else if (!isChecked && current.includes(request)) {
      this.form.controls.specialRequests.setValue(current.filter(r => r !== request));
    }
    this.form.controls.specialRequests.markAsDirty();
  }

  onStartDateChange(date: string): void {
    this.form.controls.checkInDate.setValue(date);
  }

  onEndDateChange(date: string): void {
    this.form.controls.checkOutDate.setValue(date);
  }
}
