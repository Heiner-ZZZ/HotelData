import { CurrencyPipe } from '@angular/common';
import { HttpClient, httpResource, HttpParams } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal, ViewEncapsulation } from '@angular/core';
import type { AbstractControl, ValidationErrors } from '@angular/forms';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, EMPTY, switchMap, debounceTime } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { AuthService } from '../../../../core/auth/auth.service';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ReservationsAuthService } from '../../services/reservations-auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { RnPlannerSectionComponent } from './partials/rn-planner-section';
import { RnGuestSectionComponent } from './partials/rn-guest-section';
import { RnReviewSectionComponent } from './partials/rn-review-section';
import { availabilityInfoFor } from './partials/reservation-form-messages';
import type { RatePlanOption, ReservationCreateInput, ReservationPreview } from '../../models/reservations.model';
import { ReservationsApiService } from '../../services/reservations-api.service';
import { GuestAmenityService } from '../../../amenities/services/guest-amenity.service';
import type { GuestAmenityCategoryDto, GuestSpecialRequestDto } from '../../../amenities/models/guest-amenity.dto';

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

/** One selectable special request in "Peticiones especiales". */
export interface SpecialRequestOption {
  value: string;
  label: string;
  unit_price: number;
  chargeable: boolean;
  pet_related: boolean;
  high_floor: boolean;
  late_arrival: boolean;
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
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly guestAmenityService = inject(GuestAmenityService);
  private readonly http = inject(HttpClient);
  private readonly operationMode = inject(OperationModeService);

  // ─── Form ─── (declared BEFORE the toSignal fields that read it)
  // Validadores por caja: teléfono solo permite + (no -), cédula solo permite - (no +)
  // según requerimiento de negocio celular vs cédula.
  readonly form = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]],
    guestName: ['', [Validators.required]],
    guestEmail: ['', [Validators.required, Validators.email]],
    guestPhone: ['', [
      Validators.required,
      Validators.minLength(7),
      Validators.maxLength(20),
      Validators.pattern(/^\+?[0-9\s\(\)\.]*$/),
    ]],
    checkInDate: ['', [Validators.required]],
    checkOutDate: ['', [Validators.required]],
    // Standard overnight booking requires both arrival and departure times.
    // These are editable defaults sourced from the hotel policy (see the
    // policiesResource effect below); the backend validates them against the
    // hotel's configured policy hours.
    checkInTime: ['', [Validators.required]],
    checkOutTime: ['', [Validators.required]],
    // Hora estimada de llegada (opcional, HH:MM). Al superar las 20:00 (o al
    // marcar la petición "Llegada tarde") la reserva se marca como late check-in.
    estimatedArrivalTime: [''],
    adults: [2, [Validators.required, Validators.min(1), Validators.max(20)]],
    children: [0, [Validators.required, Validators.min(0), Validators.max(10)]],
    rooms: [1, [Validators.required, Validators.min(1), Validators.max(10)]],
    comment: [''],
    couponCode: [''],
    specialRequests: [[] as string[]],
    cedula: ['', [
      Validators.required,
      Validators.minLength(6),
      Validators.maxLength(20),
      Validators.pattern(/^[0-9\-]*$/),
    ]],
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

  /** Per-hotel availability — re-fires when propId or any date signal changes.
   *  Guards on `isAuthenticated()` so the request only fires once the session
   *  cookie is settled, avoiding 401/403 loops right after login. */
  readonly availabilityResource = httpResource<{
    hasInventory: boolean;
    hasRoomTypes: boolean;
    totalRooms: number;
    availableRooms: number;
    message: string;
  }>(() => {
    if (!this.authService.isAuthenticated()) return undefined;
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

  /** Available rate plans for the selected hotel + dates + optional room type.
   *  Guards on `isAuthenticated()` to avoid firing before the session cookie is ready. */
  readonly ratePlansResource = httpResource<RatePlanOption[]>(() => {
    if (!this.authService.isAuthenticated()) return undefined;
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
  readonly amenityResource = httpResource<{ catalog: GuestAmenityCategoryDto[]; special_requests?: GuestSpecialRequestDto[] }>(() => {
    const propId = this.propIdSignal();
    if (!propId) return undefined;
    return {
      url: '/amenities/guest/catalog/by-prop',
      method: 'GET' as const,
      params: new HttpParams().set('prop_id', String(propId)),
    };
  });

  /** Hotel policy defaults (check-in/check-out hours) — re-fires when propId changes. */
  readonly policiesResource = httpResource<{ policies?: { check_in_time?: string; check_out_time?: string } }>(() => {
    const propId = this.propIdSignal();
    if (!propId) return undefined;
    return {
      url: '/management/policies',
      method: 'GET' as const,
      params: new HttpParams().set('prop_id', String(propId)),
    };
  });

  // ─── Writable signals ───
  // The shared property selector owns the hotel catalog/loading state. This
  // page only keeps the selected id in the reactive form.
  readonly loading = signal(false);
  readonly submitting = signal(false);
  readonly previewing = signal(false);
  readonly errorMessage = signal('');
  readonly preview = signal<ReservationPreview | null>(null);
  readonly step = signal<'details' | 'review'>('details');

  /** Depósito real (política de pago por adelantado): método y referencia
   *  que se registran como pago de billing al confirmar la reserva. */
  readonly depositMethod = signal('cash');
  readonly depositReference = signal('');

  /** Room type and physical room passed from the reception Timeline. */
  readonly preselectedRoomTypeId = signal('');
  readonly preselectedRoomTypeName = signal('');
  readonly preselectedHotelRoomId = signal('');
  readonly preselectedRoomNumber = signal('');

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
  readonly specialRequestsCatalog = signal<GuestSpecialRequestDto[]>([]);

  /** label → unit_price for the review step chips (special requests). */
  readonly specialRequestPriceMap = computed(() => {
    const map = new Map<string, number>();
    for (const r of this.specialRequestOptions()) map.set(r.label, r.unit_price);
    return map;
  });

  /** label → unit_price for the review step chips (amenities). */
  readonly amenityPriceMap = computed(() => {
    const map = new Map<string, number>();
    for (const cat of this.amenityCatalog()) {
      for (const item of cat.items) map.set(item.label, item.unit_price);
    }
    return map;
  });

  /** Hotel whose policy times were last auto-filled (0 = never). */
  private lastPolicyPropId = 0;

  /** Policy hours (HH:MM) for the selected hotel, from the policies endpoint. */
  readonly policyCheckInTime = computed(() => this.policiesResource.value()?.policies?.check_in_time ?? '');
  readonly policyCheckOutTime = computed(() => this.policiesResource.value()?.policies?.check_out_time ?? '');

  /**
   * Display label for the review step. Shows the form values (what the user is
   * actually booking) with the policy hours as fallback when still empty.
   */
  readonly checkInOutPolicyLabel = computed(() => {
    const checkIn = this.form.controls.checkInTime.value || this.policyCheckInTime();
    const checkOut = this.form.controls.checkOutTime.value || this.policyCheckOutTime();
    if (!checkIn && !checkOut) return '';
    return `Check-in desde las ${checkIn || '—'} · Check-out hasta las ${checkOut || '—'}`;
  });

  readonly availableRatePlans = signal<RatePlanOption[]>([]);
  readonly ratePlansLoading = signal(false);
  readonly selectedRatePlanId = signal('');

  readonly isStaff = this.reservationsAuth.isStaff;
  readonly isClient = this.reservationsAuth.isClient;

  /** ID exposed to the planner so the shared selector stays in sync with the form. */
  readonly selectedPropId = computed(() => this.propIdSignal());

  /** Label comes from the shared property context after selection. */
  readonly selectedLabel = computed(() => this.propertyCtx.currentPropLabel());

  /**
   * The planner needs a hotel object for its metadata and downstream sections.
   * The shared selector owns the authoritative label; before it resolves an
   * initial URL id, keep the UI useful with a non-empty fallback.
   */
  readonly selectedHotel = computed(() => {
    const selectedId = this.propIdSignal();
    if (!selectedId) return null;
    return {
      propId: selectedId,
      label: this.selectedLabel() || `Hotel ${selectedId}`,
    };
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
  getHotelAvailabilityInfo(propId: number): { label: string; icon: string; color: string; message?: string } | null {
    return availabilityInfoFor(this.hotelAvailabilityStatus()[propId], this.availabilityResource.value()?.message);
  }

  /**
   * Special-request options shown in "Peticiones especiales".
   *
   * Loaded from the per-hotel catalog (``/amenities/guest/catalog/by-prop``
   * → ``special_requests``) with prices and behavior flags. Only the hotel's
   * ACTIVE requests are offered: the backend already excludes the defaults
   * the hotel deleted (``removed_requests`` tombstones). No hardcoded
   * fallback — an empty catalog means no requests are available.
   */
  readonly specialRequestOptions = computed<SpecialRequestOption[]>(() =>
    this.specialRequestsCatalog().map((r) => ({
      value: r.label,
      label: r.label,
      unit_price: r.unit_price,
      chargeable: r.chargeable,
      pet_related: r.pet_related,
      high_floor: r.high_floor,
      late_arrival: r.late_arrival,
    })),
  );

  readonly today = new Date().toISOString().split('T')[0];

  constructor() {
    const prefixedPropId = Number(this.activatedRoute.snapshot.queryParamMap.get('prop_id') ?? '0');
    const prefixedRoomType = this.activatedRoute.snapshot.queryParamMap.get('room_type') ?? '';
    const prefixedRoomTypeName = this.activatedRoute.snapshot.queryParamMap.get('room_type_name') ?? '';
    const prefixedHotelRoomId = this.activatedRoute.snapshot.queryParamMap.get('hotel_room_id') ?? '';
    const prefixedRoomNumber = this.activatedRoute.snapshot.queryParamMap.get('room_number') ?? '';
    const prefixedCheckIn = this.activatedRoute.snapshot.queryParamMap.get('check_in') ?? '';
    const prefixedCheckOut = this.activatedRoute.snapshot.queryParamMap.get('check_out') ?? '';
    const prefixedCheckInTime = this.activatedRoute.snapshot.queryParamMap.get('check_in_time') ?? '';
    const prefixedCheckOutTime = this.activatedRoute.snapshot.queryParamMap.get('check_out_time') ?? '';
    if (prefixedPropId > 0) {
      this.form.controls.propId.setValue(prefixedPropId);
    }
    if (prefixedRoomType) {
      this.preselectedRoomTypeId.set(prefixedRoomType);
      this.preselectedRoomTypeName.set(prefixedRoomTypeName);
    }
    if (prefixedHotelRoomId) {
      this.preselectedHotelRoomId.set(prefixedHotelRoomId);
      this.preselectedRoomNumber.set(prefixedRoomNumber);
    }
    // Dates from URL query params ALWAYS take precedence over Redis.
    const hasUrlDates = !!(prefixedCheckIn || prefixedCheckOut || prefixedCheckInTime || prefixedCheckOutTime);
    if (hasUrlDates) {
      this.form.patchValue({
        checkInDate: prefixedCheckIn,
        checkOutDate: prefixedCheckOut,
        checkInTime: prefixedCheckInTime || this.form.controls.checkInTime.value,
        checkOutTime: prefixedCheckOutTime || this.form.controls.checkOutTime.value,
      });
    } else {
      // No dates in URL → load from Redis (guest session prefs persisted from search page)
      this._loadSearchPrefsFromRedis();
    }
    this._loadGuestSuggestions();
    this._restoreGuestDraft();
    this._persistGuestDraft();

    // ── Sanitización en vivo: teléfono solo + (no -), cédula solo - (no +) ──
    this.form.controls.guestPhone.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((v) => {
      if (typeof v !== 'string') return;
      let filtered = v.replace(/[^0-9\s\(\)\.+]/g, '');
      filtered = filtered.replace(/-/g, '');
      const plusMatches = filtered.match(/\+/g) || [];
      if (plusMatches.length > 1) {
        filtered = '+' + filtered.replace(/\+/g, '');
      }
      if (filtered.includes('+') && !filtered.startsWith('+')) {
        filtered = filtered.replace(/\+/g, '');
      }
      if (filtered !== v) {
        this.form.controls.guestPhone.setValue(filtered, { emitEvent: false });
      }
    });
    this.form.controls.cedula.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((v) => {
      if (typeof v !== 'string') return;
      let filtered = v.replace(/[^0-9\-]/g, '');
      filtered = filtered.replace(/\+/g, '');
      filtered = filtered.replace(/--+/g, '-');
      if (filtered !== v) {
        this.form.controls.cedula.setValue(filtered, { emitEvent: false });
      }
    });

    // The shared property selector handles hotel catalog loading. Once it
    // emits a property, the form control drives all dependent resources below.

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

    // amenityResource.value() → amenityCatalog + specialRequestsCatalog (success).
    effect(() => {
      const r = this.amenityResource.value();
      if (!r) return;
      this.amenityCatalog.set(r.catalog || []);
      this.specialRequestsCatalog.set(r.special_requests || []);
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

    // policiesResource.value() → prefill check-in/check-out hours from the
    // hotel policy. Only fills the fields when they are still empty so the
    // user's own input (or the query-param prefill from the Timeline) wins.
    // When the hotel changes and the user hasn't edited the times, the stale
    // values from the previous hotel are cleared so the new policy applies.
    effect(() => {
      const propId = this.propIdSignal();
      const policy = this.policiesResource.value();
      const checkInControl = this.form.controls.checkInTime;
      const checkOutControl = this.form.controls.checkOutTime;
      // Al cambiar de hotel, limpia únicamente los campos pristine (no
      // editados por el usuario) para que la política nueva (si existe) los
      // rellene. Los campos que el usuario editó se conservan. Se ejecuta
      // antes del guard de respuesta para que también se limpie cuando la
      // política del nuevo hotel falla al cargar.
      if (this.lastPolicyPropId !== 0 && this.lastPolicyPropId !== propId) {
        if (!checkInControl.dirty) checkInControl.setValue('');
        if (!checkOutControl.dirty) checkOutControl.setValue('');
        this.lastPolicyPropId = propId;
      }
      if (!policy?.policies) return;
      const checkIn = policy.policies.check_in_time;
      const checkOut = policy.policies.check_out_time;
      if (checkIn && !checkInControl.value) {
        checkInControl.setValue(checkIn);
      }
      if (checkOut && !checkOutControl.value) {
        checkOutControl.setValue(checkOut);
      }
      this.lastPolicyPropId = propId;
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
      // Pre-fill cedula from profile if guest has DNI or passport saved
      this.http.get<{ id_document_type?: string; id_document_number?: string }>('/account/profile')
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (profile) => {
            const docType = profile?.id_document_type ?? '';
            const docNumber = profile?.id_document_number ?? '';
            if ((docType === 'dni' || docType === 'passport') && docNumber) {
              this.form.controls.cedula.setValue(docNumber);
            }
          },
          error: () => { /* Profile unavailable — cedula stays empty, guest enters manually */ },
        });
    }
  }

  goToReview() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.toast.warning('Hay campos obligatorios sin completar o fechas inválidas. Completá los campos marcados en rojo y ajustá las fechas para continuar.');
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
          this.toast.error('No se pudo calcular la disponibilidad y el precio. Revisá el hotel y las fechas seleccionadas, e intentá de nuevo.');
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
      estimatedArrivalTime: v.estimatedArrivalTime || undefined,
      adults: v.adults,
      children: v.children,
      rooms: v.rooms,
      comment: v.comment,
      couponCode: v.couponCode,
      specialRequests: v.specialRequests,
      selectedAmenities: [...this.selectedAmenities()],
      roomTypeId: this.preselectedRoomTypeId() || undefined,
      hotelRoomId: this.preselectedHotelRoomId() || undefined,
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
      this.toast.error('No hay habitaciones disponibles para las fechas seleccionadas. Probá con otras fechas o elegí otro hotel.');
      this.step.set('details');
      return;
    }
    this.doCreate();
  }

  private doCreate() {
    const v = this.form.getRawValue();
    this._saveGuestSuggestion(v.guestName, v.guestEmail, v.guestPhone);

    this.submitting.set(true);
    this.errorMessage.set('');

    const payload = this.buildPayload();
    // Política de pago por adelantado: el depósito mínimo se registra como
    // pago REAL de billing (con shift_id del turno) en la misma llamada.
    const previewData = this.preview();
    if (previewData?.depositRequired) {
      payload.deposit = {
        amount: previewData.minDepositAmount ?? 0,
        method: this.depositMethod(),
        reference: this.depositReference().trim() || undefined,
      };
    }

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

  /** Handle the shared selector without duplicating hotel-option logic here. */
  onPropertySelected(event: { propId: number; label: string }): void {
    const propId = event.propId || 0;
    if (propId) {
      this.propertyCtx.setProperty(propId, event.label || `Propiedad #${propId}`);
    } else {
      this.propertyCtx.clear();
    }
    this.form.controls.propId.setValue(propId);
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: propId || null },
      queryParamsHandling: 'merge',
    });
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
    this.reservationsApi.validateCoupon(code, propId, {
      checkIn: this.form.controls.checkInDate.value || undefined,
      checkOut: this.form.controls.checkOutDate.value || undefined,
      ratePlanId: this.selectedRatePlanId() || undefined,
      roomTypeId: this.preselectedRoomTypeId() || this.form.controls.rooms.value ? undefined : undefined,
    }).subscribe({
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
    // Al marcar la petición "Llegada tarde" sin hora estimada, se sugiere la
    // hora convencional de late check-in (20:00) para que el marcador aplique.
    if (isChecked && this._isLateArrivalRequest(request) && !this.form.controls.estimatedArrivalTime.value) {
      this.form.controls.estimatedArrivalTime.setValue('20:00');
    }
  }

  /** True si la petición marcada está flaggeada como late_arrival en el catálogo. */
  /** Load search dates from Redis (guest session prefs persisted by search page).
   *  Only called when the URL has no dates — URL always wins. */
  private _loadSearchPrefsFromRedis(): void {
    this.http.get<{ check_in?: string; check_out?: string }>('/api/guest/session-prefs')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (prefs) => {
          if (prefs?.check_in || prefs?.check_out) {
            this.form.patchValue({
              checkInDate: prefs.check_in || '',
              checkOutDate: prefs.check_out || '',
            });
          }
        },
        error: () => { /* Redis unavailable — form stays empty, user picks dates manually */ },
      });
  }

  private _isLateArrivalRequest(request: string): boolean {
    const r = this.specialRequestOptions().find((opt) => opt.value === request);
    return !!r?.late_arrival;
  }

  onStartDateChange(date: string): void {
    this.form.controls.checkInDate.setValue(date);
  }

  onEndDateChange(date: string): void {
    this.form.controls.checkOutDate.setValue(date);
  }
}
