import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { httpResource } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { toSignal } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { DateRangePickerComponent } from '../../../../shared/ui/date-range-picker/date-range-picker';
import { DestinationAutocompleteComponent } from '../../../../shared/ui/destination-autocomplete/destination-autocomplete';
import { GuestsPickerComponent } from '../../../../shared/ui/guests-picker/guests-picker';
import { API_CONFIG } from '../../../../core/api/api.config';

import {
  CURRENCY_STORAGE_KEY,
  FALLBACK_CURRENCIES,
  type FeaturedHotel,
  type SystemCurrencyDto,
} from '../../models/welcome.models';
import { currencyFlag, mapFeaturedHotels } from '../../mappers/welcome.mapper';
import {
  loadWelcomeSearchState,
  saveWelcomeSearchState,
} from '../../services/welcome-search-state';

@Component({
  selector: 'app-welcome-page',
  imports: [RouterLink, ReactiveFormsModule, DateRangePickerComponent, GuestsPickerComponent, DestinationAutocompleteComponent],
  templateUrl: './welcome-page.html',
  styleUrls: [
    '../../../../../styles/_auth-shell.scss',
    './welcome-page.scss',
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WelcomePageComponent {
  private readonly authService = inject(AuthService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly apiConfig = inject(API_CONFIG);

  readonly year = new Date().getFullYear();

  // ── Search form ─────────────────────────────────────────────────────────

  /** Hoy en fecha LOCAL (YYYY-MM-DD) — no UTC: en husos negativos,
   *  toISOString() devolvería mañana y rompería minDate + el saneo de
   *  fechas pasadas del estado guardado. */
  readonly today = (() => {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${mm}-${dd}`;
  })();

  readonly searchForm = this.formBuilder.nonNullable.group({
    destination: [''],
    checkIn: [''],
    checkOut: [''],
    adults: ['2'],
    children: ['0'],
    rooms: ['1'],
  });

  /** Fecha de entrada desde el date-range-picker compartido (mismo widget
   *  que /account/bookings/new): un solo calendario, clic o arrastre. */
  onStartDateChange(date: string): void {
    this.searchForm.controls.checkIn.setValue(date);
  }

  onEndDateChange(date: string): void {
    this.searchForm.controls.checkOut.setValue(date);
  }

  // ── Destino dinámico ──────────────────────────────────────────────────

  onDestinationChange(value: string): void {
    this.searchForm.controls.destination.setValue(value);
  }

  // ── Huéspedes (guests-picker compartido) ──────────────────────────────

  /** Snapshot reactivo del form: un toSignal sobre valueChanges para que
   *  guestCounts (y cualquier binding) se recompute al escribir controles. */
  private readonly formSnapshot = toSignal(this.searchForm.valueChanges, {
    initialValue: this.searchForm.getRawValue(),
  });

  /** Los controles guardan strings; el picker necesita números (señal reactiva). */
  readonly guestCounts = computed(() => {
    const fv = this.formSnapshot() ?? this.searchForm.getRawValue();
    return {
      adults: Number(fv.adults) || 2,
      children: Number(fv.children) || 0,
      rooms: Number(fv.rooms) || 1,
    };
  });

  onAdultsChange(value: number): void {
    this.searchForm.controls.adults.setValue(String(value));
  }

  onChildrenChange(value: number): void {
    this.searchForm.controls.children.setValue(String(value));
  }

  onRoomsChange(value: number): void {
    this.searchForm.controls.rooms.setValue(String(value));
  }

  navigateToSearch(): void {
    const fv = this.searchForm.getRawValue();
    const params: Record<string, string> = {};
    if (fv.destination.trim()) params['destination'] = fv.destination.trim();
    if (fv.checkIn) params['check_in'] = fv.checkIn;
    if (fv.checkOut) params['check_out'] = fv.checkOut;
    if (fv.adults !== '2') params['adults'] = fv.adults;
    if (fv.children !== '0') params['children'] = fv.children;
    if (fv.rooms !== '1') params['rooms'] = fv.rooms;

    // Persistir antes de navegar: al volver al welcome el booking bar
    // recarga estos valores (ver constructor).
    this.persistSearchState();

    const qs = new URLSearchParams(params).toString();
    void this.router.navigateByUrl(qs ? `/search?${qs}` : '/search');
  }

  /** Serializa el estado actual del booking bar (fuente única del mapping). */
  private serializeForm() {
    const fv = this.searchForm.getRawValue();
    return {
      destination: fv.destination.trim(),
      checkIn: fv.checkIn,
      checkOut: fv.checkOut,
      adults: Number(fv.adults) || 2,
      children: Number(fv.children) || 0,
      rooms: Number(fv.rooms) || 1,
    };
  }

  /** Persiste el estado actual del booking bar a localStorage. */
  private persistSearchState(): void {
    saveWelcomeSearchState(this.serializeForm());
  }

  // ── Featured hotels ─────────────────────────────────────────────────────

  readonly featuredHotelsResource = httpResource<{ items: FeaturedHotel[] }>(
    () => `${this.apiConfig.baseUrl}/hotels/availability?sort_by=rating&page_size=3&content_only=true`,
    {
      parse: (dto) => ({ items: mapFeaturedHotels(dto as { items?: {
        prop_id: number; display_name: string; prop_starrating: number | null;
        prop_review_score: number | null; image_url: string | null;
        destination_labels: string[]; min_nightly_rate_label: string | null;
      }[] }) }),
    },
  );

  readonly featuredHotels = computed(() => this.featuredHotelsResource.value()?.items ?? []);

  hotelDetailHref(propId: number): string {
    return `/hotels/${propId}`;
  }

  readonly STAR_5 = [0, 1, 2, 3, 4];

  // ── Auth toast ──────────────────────────────────────────────────────────

  readonly showAuthToast = signal(false);
  private authToastTimer: ReturnType<typeof setTimeout> | null = null;

  handleHotelClick(hotelId: number, event: Event): void {
    event.preventDefault();
    if (this.authService.isAuthenticated()) {
      void this.router.navigateByUrl(`/hotels/${hotelId}`);
      return;
    }
    if (this.authToastTimer) clearTimeout(this.authToastTimer);
    this.showAuthToast.set(true);
    this.authToastTimer = setTimeout(() => this.dismissAuthToast(), 8000);
  }

  dismissAuthToast(): void {
    if (this.authToastTimer) { clearTimeout(this.authToastTimer); this.authToastTimer = null; }
    this.showAuthToast.set(false);
  }

  readonly hasSession = computed(
    () => this.authService.isAuthenticated() && this.authService.sessionLoaded(),
  );

  // ── Currency chip ───────────────────────────────────────────────────────

  readonly currenciesResource = httpResource<{ currencies: SystemCurrencyDto[] }>(
    () => `${this.apiConfig.baseUrl}/public/currencies`,
    {
      parse: (dto) => {
        const raw = (dto as { currencies?: SystemCurrencyDto[] })?.currencies ?? [];
        const cleaned = raw.filter((c) => c?.code && c.active !== false);
        return { currencies: cleaned.length ? cleaned : [...FALLBACK_CURRENCIES] };
      },
    },
  );

  readonly currencies = computed<readonly SystemCurrencyDto[]>(() => {
    const fromApi = this.currenciesResource.value()?.currencies;
    return fromApi && fromApi.length ? fromApi : FALLBACK_CURRENCIES;
  });

  readonly selectedCurrency = signal<string>(this.readStoredCurrency());

  constructor() {
    // Precarga el último booking bar guardado (destino, fechas, huéspedes).
    // loadWelcomeSearchState saneja fechas pasadas y rangos inválidos.
    const saved = loadWelcomeSearchState(this.today);
    if (saved) {
      this.searchForm.patchValue({
        destination: saved.destination,
        checkIn: saved.checkIn,
        checkOut: saved.checkOut,
        adults: String(saved.adults),
        children: String(saved.children),
        rooms: String(saved.rooms),
      });
    }

    effect(() => {
      if (this.hasSession()) {
        const homeHref = this.authService.authState().homeHref;
        void this.router.navigateByUrl(this.authService.resolveDefaultDestination(homeHref));
      }
    });

    effect(() => {
      const code = this.selectedCurrency();
      if (!code) return;
      this.propertyCtx.setCurrency(code, [code]);
    });

    // Persistencia en vivo (debounced): si el usuario edita el booking bar
    // pero navega a otra parte sin pulsar Buscar, el estado no se pierde.
    // El destination-autocomplete emite por carácter, así que el debounce
    // evita escribir localStorage en cada tecla. onCleanup cancela el timer
    // si el componente se destruye antes de los 600ms.
    effect((onCleanup) => {
      const fv = this.formSnapshot();
      if (!fv) return;
      const timer = setTimeout(() => {
        saveWelcomeSearchState(this.serializeForm());
      }, 600);
      onCleanup(() => clearTimeout(timer));
    });
  }

  onCurrencyChange(code: string): void {
    if (!code || code === this.selectedCurrency()) return;
    this.selectedCurrency.set(code);
    this.writeStoredCurrency(code);
  }

  /** Delegates to the mapper for the flag emoji. */
  currencyFlag(code: string): string {
    return currencyFlag(code);
  }

  // ── LocalStorage helpers ────────────────────────────────────────────────

  private readStoredCurrency(): string {
    const v = localStorage.getItem(CURRENCY_STORAGE_KEY);
    if (v && v.trim().length === 3) return v.trim().toUpperCase();
    // First-time visitor: fall back to the property context's default
    // currency (also 'USD' on a fresh install, but this codepath keeps the
    // single source of truth in PropertyContextService instead of leaking
    // a literal that drifts over time).
    return this.propertyCtx.currentCurrency();
  }

  private writeStoredCurrency(code: string): void {
    localStorage.setItem(CURRENCY_STORAGE_KEY, code.toUpperCase());
  }
}
