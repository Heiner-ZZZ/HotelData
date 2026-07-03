import { CurrencyPipe, DatePipe, UpperCasePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, EMPTY, Subject, switchMap, debounceTime } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { AuthService } from '../../../../core/auth/auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { DateRangePickerComponent } from '../../../../shared/ui/date-range-picker/date-range-picker';
import { RnPlannerSectionComponent } from './partials/rn-planner-section';
import { RnGuestSectionComponent } from './partials/rn-guest-section';
import { RnReviewSectionComponent } from './partials/rn-review-section';
import type { RatePlanOption, ReservationCreateInput, ReservationHotelOption, ReservationPreview } from '../../models/reservations.model';
import { ReservationsApiService } from '../../services/reservations-api.service';
import { GuestAmenityService } from '../../../amenities/services/guest-amenity.service';
import type { GuestAmenityCategoryDto, GuestAmenityItemDto } from '../../../amenities/models/guest-amenity.dto';

@Component({
  selector: 'app-reservation-new-page',
  imports: [CurrencyPipe, DatePipe, UpperCasePipe, DateRangePickerComponent, ReactiveFormsModule, RouterLink,
    RnPlannerSectionComponent, RnGuestSectionComponent, RnReviewSectionComponent],
  templateUrl: './reservation-new-page.html',
  styleUrl: './reservation-new-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReservationNewPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly previewing = signal(false);
  readonly errorMessage = signal('');
  readonly hotelOptions = signal<ReservationHotelOption[]>([]);
  readonly preview = signal<ReservationPreview | null>(null);
  readonly step = signal<'details' | 'review'>('details');

  /** Room type ID and name passed from hotel detail page via query params */
  readonly preselectedRoomTypeId = signal('');
  readonly preselectedRoomTypeName = signal('');

  /** Availability status per hotel: 'unknown' | 'has_inventory' | 'no_inventory' | 'checking' | 'no_room_types' */
  readonly hotelAvailabilityStatus = signal<Record<number, 'unknown' | 'has_inventory' | 'no_inventory' | 'checking' | 'no_room_types'>>({});

  readonly guestSuggestions = signal<Array<{ name: string; email: string; phone: string }>>([]);
  readonly apiUserResults = signal<Array<{ name: string; email: string; phone: string; cedula: string }>>([]);
  readonly apiSearching = signal(false);
  readonly showGuestDropdown = signal(false);
  readonly guestSearchFocused = signal(false);

  /** Subject with debounce for typing-triggered user search */
  /** Subject with debounce for typing-triggered user search — public for template access */
  readonly userSearch$ = new Subject<string>();

  readonly couponStatus = signal<{valid: boolean; message: string; discountPercent: number} | null>(null);
  readonly couponValidating = signal(false);

  // Amenities catalog & selection
  private readonly guestAmenityService = inject(GuestAmenityService);
  readonly amenityCatalog = signal<GuestAmenityCategoryDto[]>([]);
  readonly amenityCatalogLoading = signal(false);
  readonly selectedAmenities = signal<Set<string>>(new Set());
  readonly amenityCatalogError = signal('');

  /** Available rate plans for selected hotel + dates */
  readonly availableRatePlans = signal<RatePlanOption[]>([]);
  readonly ratePlansLoading = signal(false);
  readonly selectedRatePlanId = signal('');

  readonly isStaff = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;
    return role ? ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'].includes(role) : false;
  });

  readonly isClient = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;
    return !role || role === 'cliente';
  });

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

  /** Check inventory availability for a given hotel and date range */
  checkHotelAvailability(propId: number): void {
    if (!propId) return;
    const checkIn = this.form.controls.checkInDate.value;
    const checkOut = this.form.controls.checkOutDate.value;
    if (!checkIn || !checkOut) return;

    this.hotelAvailabilityStatus.update(s => ({ ...s, [propId]: 'checking' }));

    this.reservationsApi.getHotelAvailability(propId, checkIn, checkOut).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (result) => {
        const status = result.hasRoomTypes
          ? (result.hasInventory ? 'has_inventory' : 'no_inventory')
          : 'no_room_types';
        this.hotelAvailabilityStatus.update(s => ({ ...s, [propId]: status }));
      },
      error: () => {
        this.hotelAvailabilityStatus.update(s => ({ ...s, [propId]: 'unknown' }));
      },
    });
  }

  /** Availability label and icon for a given hotel */
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

  readonly form = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]],
    guestName: ['', [Validators.required]],
    guestEmail: ['', [Validators.required, Validators.email]],
    guestPhone: [''],
    checkInDate: ['', [Validators.required]],
    checkOutDate: ['', [Validators.required]],
    checkInTime: [''],
    checkOutTime: [''],
    adults: [2, [Validators.required, Validators.min(1), Validators.max(20)]],
    children: [0, [Validators.required, Validators.min(0), Validators.max(10)]],
    rooms: [1, [Validators.required, Validators.min(1), Validators.max(10)]],
    comment: [''],
    couponCode: [''],
    specialRequests: [[] as string[]],
    cedula: ['']
  });

  constructor() {
    const prefixedPropId = Number(this.activatedRoute.snapshot.queryParamMap.get('prop_id') ?? '0');
    const prefixedRoomType = this.activatedRoute.snapshot.queryParamMap.get('room_type') ?? '';
    const prefixedRoomTypeName = this.activatedRoute.snapshot.queryParamMap.get('room_type_name') ?? '';
    if (prefixedRoomType) {
      this.preselectedRoomTypeId.set(prefixedRoomType);
      this.preselectedRoomTypeName.set(prefixedRoomTypeName);
    }
    this._loadGuestSuggestions();

    // ── Search registered users on the backend when staff types ──
    this.userSearch$
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
          
          // Trigger initial availability check if hotel and dates are already selected
          if (prefixedPropId > 0 && this.form.controls.checkInDate.value && this.form.controls.checkOutDate.value) {
            this.checkHotelAvailability(prefixedPropId);
          }
        },          error: () => {
          this.toast.show('No fue posible cargar el formulario de reservas.', 'error', 6000);
          this.loading.set(false);
        }
      });

    // Load amenity catalog when hotel changes
    this.form.controls.propId.valueChanges
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        distinctUntilChanged(),
      )
      .subscribe((propId) => {
        // Reset amenity selection when hotel changes
        this.selectedAmenities.set(new Set());
        if (propId) {
          this._loadAmenityCatalog(propId);
        } else {
          this.amenityCatalog.set([]);
        }
      });

    // Reactively check availability when hotel or dates change
    this.form.controls.propId.valueChanges
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        distinctUntilChanged(),
      )
      .subscribe(() => {
        if (this.form.controls.checkInDate.value && this.form.controls.checkOutDate.value) {
          this.checkHotelAvailability(this.form.controls.propId.value);
        } else {
          this.hotelAvailabilityStatus.set({});
        }
      });

    this.form.controls.checkInDate.valueChanges
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        distinctUntilChanged(),
      )
      .subscribe(() => {
        const propId = this.form.controls.propId.value;
        const checkOut = this.form.controls.checkOutDate.value;
        if (propId && checkOut) {
          this.checkHotelAvailability(propId);
        }
        this._loadRatePlans();
      });

    this.form.controls.checkOutDate.valueChanges
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        distinctUntilChanged(),
      )
      .subscribe(() => {
        const propId = this.form.controls.propId.value;
        const checkIn = this.form.controls.checkInDate.value;
        if (propId && checkIn) {
          this.checkHotelAvailability(propId);
        }
        this._loadRatePlans();
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

  /** Load available rate plans when hotel and dates are selected */
  private _loadRatePlans(): void {
    const propId = this.form.controls.propId.value;
    const checkIn = this.form.controls.checkInDate.value;
    const checkOut = this.form.controls.checkOutDate.value;
    if (!propId || !checkIn || !checkOut) {
      this.availableRatePlans.set([]);
      return;
    }
    this.ratePlansLoading.set(true);
    this.reservationsApi.getAvailableRatePlans(
      propId, checkIn, checkOut,
      this.preselectedRoomTypeId() || undefined,
    ).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.availableRatePlans.set(result.rate_plans || []);
        this.ratePlansLoading.set(false);
        // Auto-select first plan if none selected
        const plans = result.rate_plans || [];
        if (plans.length > 0 && !this.selectedRatePlanId()) {
          this.selectedRatePlanId.set(plans[0].ratePlanId);
        }
      },
      error: () => this.ratePlansLoading.set(false),
    });
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

  private _loadAmenityCatalog(propId: number) {
    if (!propId) return;
    this.amenityCatalogLoading.set(true);
    this.amenityCatalogError.set('');
    // Use a dummy booking_id to get catalog for a prop — the guest endpoint needs it
    // Instead, directly fetch via the partner endpoint which works with prop_id
    this.guestAmenityService.getCatalogByProp(propId).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (result) => {
        this.amenityCatalog.set(result.catalog || []);
        this.amenityCatalogLoading.set(false);
      },
      error: () => {
        this.amenityCatalog.set([]);
        this.amenityCatalogLoading.set(false);
        this.amenityCatalogError.set('No se pudo cargar el catálogo de amenities.');
      },
    });
  }

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

    // ═══ GUARD: Verificar disponibilidad antes de enviar ═══
    const previewData = this.preview();
    if (previewData && !previewData.available) {
      this.toast.show('No hay habitaciones disponibles para las fechas seleccionadas. Intenta con otras fechas o reduce el número de huéspedes.', 'error', 6000);
      this.step.set('details');
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
          void this.router.navigate(['../confirmed', result.bookingId], { relativeTo: this.activatedRoute });
        },
        error: (error: ApiError) => {
          const msg = error.message || '';
          if (msg.includes('No inventory data') || msg.includes('inventory')) {
            this.toast.show('No hay habitaciones disponibles para las fechas seleccionadas. Por favor, intenta con otras fechas.', 'error', 6000);
          } else if (msg.includes('available')) {
            this.toast.show('No hay suficientes habitaciones disponibles para las fechas seleccionadas. Intenta reducir el número de habitaciones.', 'error', 6000);
          } else {
            this.toast.show(msg || 'No fue posible crear la reserva. Intenta de nuevo más tarde.', 'error', 6000);
          }
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

  /** Combined guest suggestions: localStorage recent guests + API search results */
  readonly filteredGuestSuggestions = computed(() => {
    const query = this.form.controls.guestName.value.toLowerCase().trim();
    const localGuests = this.guestSuggestions();
    const apiGuests = this.apiUserResults();

    // Show only recent guests when no query
    if (!query || query.length < 1) {
      return localGuests.map(g => ({ ...g, cedula: '', source: 'local' as const }));
    }

    // Merge: API results shown first, then matching localStorage entries (filter out dupes by email)
    const apiEmails = new Set(apiGuests.map(g => g.email.toLowerCase()));
    const merged: Array<{ name: string; email: string; phone: string; cedula: string; source: 'api' | 'local' }> = [
      ...apiGuests.map(g => ({ ...g, source: 'api' as const })),
      ...localGuests
        .filter(g => !apiEmails.has(g.email.toLowerCase()))
        .filter(g => g.name.toLowerCase().includes(query) || g.email.toLowerCase().includes(query))
        .map(g => ({ ...g, cedula: '', source: 'local' as const })),
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
  }

  /** Toggle guest dropdown visibility */
  toggleGuestDropdown(show: boolean) {
    // Small delay to allow click events on dropdown items
    setTimeout(() => {
      if (!show && !this.guestSearchFocused()) return;
      this.showGuestDropdown.set(show);
    }, 150);
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
