import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { httpResource } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { BookingSearchBarComponent, type BookingSearchValues } from '../../../../shared/ui/booking-search-bar/booking-search-bar';
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
  imports: [RouterLink, BookingSearchBarComponent],
  templateUrl: './welcome-page.html',
  styleUrls: [
    '../../../../../styles/_auth-shell.scss',
    './welcome-page.scss',
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WelcomePageComponent {
  private readonly authService = inject(AuthService);
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

  /** Estado inicial del booking-bar compartido: lo que el usuario dejó
   *  guardado la última vez (o defaults si no hay nada persistido). */
  readonly initialSearch: BookingSearchValues =
    loadWelcomeSearchState(this.today) ?? { destination: '', checkIn: '', checkOut: '', adults: 2, children: 0, rooms: 1 };

  /** Último valor del booking-bar (para persistencia en vivo debounced). */
  private readonly latestValues = signal<BookingSearchValues>(this.initialSearch);

  /** Persistencia en vivo: cada cambio del booking-bar se guarda (debounced)
   *  para que al volver al welcome el estado no se pierda. */
  onValueChange(values: BookingSearchValues): void {
    this.latestValues.set(values);
  }

  /** Buscar: persiste y navega a /search con los query params canónicos
   *  (omite los valores por defecto para mantener la URL limpia). */
  onSearch(values: BookingSearchValues): void {
    this.persistSearchState(values);

    const params: Record<string, string> = {};
    if (values.destination.trim()) params['destination'] = values.destination.trim();
    if (values.checkIn) params['check_in'] = values.checkIn;
    if (values.checkOut) params['check_out'] = values.checkOut;
    if (values.adults !== 2) params['adults'] = String(values.adults);
    if (values.children !== 0) params['children'] = String(values.children);
    if (values.rooms !== 1) params['rooms'] = String(values.rooms);

    const qs = new URLSearchParams(params).toString();
    void this.router.navigateByUrl(qs ? `/search?${qs}` : '/search');
  }

  /** Persiste el estado del booking bar a localStorage (tolerante a fallos). */
  private persistSearchState(values: BookingSearchValues): void {
    saveWelcomeSearchState(values);
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
      const values = this.latestValues();
      const timer = setTimeout(() => {
        saveWelcomeSearchState(values);
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
