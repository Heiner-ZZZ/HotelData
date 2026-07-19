import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal
} from '@angular/core';
import { httpResource } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { PropertyContextService } from '../../shared/services/property-context.service';
import { API_CONFIG } from '../../core/api/api.config';

/** Featured hotel card shown on the welcome landing. */
interface FeaturedHotel {
  readonly id: number;
  readonly name: string;
  readonly location: string;
  readonly stars: number | null;
  readonly score: number | null;
  readonly imageUrl: string | null;
  readonly rateLabel: string | null;
}

interface WelcomeCategory {
  readonly key: string;
  readonly label: string;
  readonly icon: string;
}

/** Shape of a row in the `system_currencies` collection (MongoDB). */
interface SystemCurrencyDto {
  readonly code: string;
  readonly name: string;
  readonly symbol: string;
  readonly decimals: number;
  readonly active: boolean;
}

/**
 * Single-tab category list. Hoisted to module scope as a placeholder so
 * a future dev restoring multi-tab navigation has one source of truth for
 * the data — see the @for restoration note next to the tab strip in
 * welcome-page.html. Currently unused because the tab strip in HTML is
 * hardcoded to a single `<button class="welcome-tab is-active">`.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const CATEGORIES: readonly WelcomeCategory[] = [
  { key: 'hotels', label: 'Hoteles', icon: 'hotel' }
];

const CURRENCY_STORAGE_KEY = 'hoteldata.preferred_currency';
const FALLBACK_CURRENCIES: readonly SystemCurrencyDto[] = [
  { code: 'USD', name: 'Dólar estadounidense', symbol: '$', decimals: 2, active: true },
  { code: 'MXN', name: 'Peso mexicano',         symbol: '$', decimals: 2, active: true },
  { code: 'EUR', name: 'Euro',                  symbol: '€', decimals: 2, active: true },
  { code: 'COP', name: 'Peso colombiano',       symbol: '$', decimals: 0, active: true }
];

@Component({
  selector: 'app-welcome-page',
  imports: [RouterLink, ReactiveFormsModule],
  templateUrl: './welcome-page.html',
  styleUrls: [
    '../../../styles/_auth-shell.scss',
    './welcome-page.scss'
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class WelcomePageComponent {
  private readonly authService = inject(AuthService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly apiConfig = inject(API_CONFIG);

  readonly year = new Date().getFullYear();

  // ── Search form ─────────────────────────────────────────────────────────
  readonly today = new Date().toISOString().split('T')[0];

  readonly searchForm = this.formBuilder.nonNullable.group({
    destination: [''],
    checkIn: ['', Validators.required],
    checkOut: ['', Validators.required],
    adults: ['2'],
    children: ['0'],
    rooms: ['1'],
  });

  readonly guestRange = [1, 2, 3, 4, 5, 6, 7, 8, 9];
  readonly childRange = [0, 1, 2, 3, 4, 5, 6];
  readonly roomRange = [1, 2, 3, 4, 5];

  /** Minimum check-out date — always at least today, and at least checkIn + 1 day. */
  readonly minCheckOut = signal(this.today);

  /** Update minCheckOut when checkIn changes so check-out can't be before check-in. */
  onCheckInChange(): void {
    const ci = this.searchForm.controls.checkIn.value;
    if (ci) {
      const next = new Date(ci);
      next.setDate(next.getDate() + 1);
      this.minCheckOut.set(next.toISOString().split('T')[0]);
      // Clear checkOut if it's now before the new minimum
      const co = this.searchForm.controls.checkOut.value;
      if (co && co <= ci) {
        this.searchForm.controls.checkOut.setValue('');
      }
    } else {
      this.minCheckOut.set(this.today);
    }
  }

  /** Navigate to /search with the form values as query params. */
  navigateToSearch(): void {
    if (this.searchForm.invalid) {
      this.searchForm.markAllAsTouched();
      return;
    }

    const fv = this.searchForm.getRawValue();
    const params: Record<string, string> = {};
    if (fv.destination.trim()) params['destination'] = fv.destination.trim();
    if (fv.checkIn) params['check_in'] = fv.checkIn;
    if (fv.checkOut) params['check_out'] = fv.checkOut;
    if (fv.adults !== '2') params['adults'] = fv.adults;
    if (fv.children !== '0') params['children'] = fv.children;
    if (fv.rooms !== '1') params['rooms'] = fv.rooms;

    const qs = new URLSearchParams(params).toString();
    void this.router.navigateByUrl(qs ? `/search?${qs}` : '/search');
  }

  // ── Featured hotels (public, no-auth) ───────────────────────────────────

  readonly featuredHotelsResource = httpResource<{ items: FeaturedHotel[] }>(
    () => `${this.apiConfig.baseUrl}/hotels/availability?sort_by=rating&page_size=3`,
    {
      parse: (dto) => {
        const raw = dto as { items?: Array<{
          prop_id: number; display_name: string; prop_starrating: number | null;
          prop_review_score: number | null; image_url: string | null;
          destination_labels: string[]; min_nightly_rate_label: string | null;
        }> };
        const items: FeaturedHotel[] = (raw.items ?? []).map((h) => ({
          id: h.prop_id,
          name: h.display_name,
          location: (h.destination_labels ?? [])[0] ?? '',
          stars: h.prop_starrating,
          score: h.prop_review_score,
          imageUrl: h.image_url,
          rateLabel: h.min_nightly_rate_label,
        }));
        return { items };
      }
    }
  );

  readonly featuredHotels = computed(() => this.featuredHotelsResource.value()?.items ?? []);

  /** Hotel detail link for the featured cards. */
  hotelDetailHref(propId: number): string {
    return `/hotels/${propId}`;
  }

  /** Star rating as an array for the *ngFor-style loop in the template. */
  starArray(n: number | null): number[] {
    return Array.from({ length: n ?? 0 }, (_, i) => i);
  }

  // ── Auth toast (slide-down banner for unauthenticated hotel clicks) ─────

  readonly showAuthToast = signal(false);
  private authToastTimer: ReturnType<typeof setTimeout> | null = null;

  /** Handle click on a featured hotel card. If not authenticated, show the
   *  register/login toast instead of navigating (prevents 401 errors). */
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

  /** Dismiss the auth toast banner. */
  dismissAuthToast(): void {
    if (this.authToastTimer) { clearTimeout(this.authToastTimer); this.authToastTimer = null; }
    this.showAuthToast.set(false);
  }

  /** Whether the user has an active session — drives the redirect effect below. */
  readonly hasSession = computed(
    () => this.authService.isAuthenticated() && this.authService.sessionLoaded()
  );

  // ── Currency chip wiring ─────────────────────────────────────────────────

  /**
   * Public, no-auth currencies endpoint. Falls back to a curated LATAM
   * subset so the chip is never empty if the backend is unreachable.
   */
  readonly currenciesResource = httpResource<{
    currencies: SystemCurrencyDto[]
  }>(() => `${this.apiConfig.baseUrl}/public/currencies`, {
    parse: (dto) => {
      const raw = (dto as { currencies?: SystemCurrencyDto[] })?.currencies ?? [];
      const cleaned = raw.filter((c) => c?.code && c.active !== false);
      return { currencies: cleaned.length ? cleaned : [...FALLBACK_CURRENCIES] };
    }
  });

  /** Resolves the dropdown options regardless of resource state. */
  readonly currencies = computed<readonly SystemCurrencyDto[]>(() => {
    const fromApi = this.currenciesResource.value()?.currencies;
    return fromApi && fromApi.length ? fromApi : FALLBACK_CURRENCIES;
  });

  /** Currency the user picked — initialised from localStorage when present. */
  readonly selectedCurrency = signal<string>(this.readStoredCurrency());

  constructor() {
    // Auto-redirect authenticated visitors straight to their dashboard.
    effect(() => {
      if (this.hasSession()) {
        const homeHref = this.authService.authState().homeHref;
        void this.router.navigateByUrl(this.authService.resolveDefaultDestination(homeHref));
      }
    });

    // Propagate currency choice to PropertyContextService for downstream pipes.
    effect(() => {
      const code = this.selectedCurrency();
      if (!code) return;
      this.propertyCtx.setCurrency(code, [code]);
    });
  }

  /** Persist + propagate currency choice when the user changes the chip. */
  onCurrencyChange(code: string): void {
    if (!code || code === this.selectedCurrency()) return;
    this.selectedCurrency.set(code);
    this.writeStoredCurrency(code);
  }

  /** Convierte código ISO de moneda (USD, MXN, EUR...) a emoji de bandera. */
  currencyFlag(code: string): string {
    const cc = code === 'EUR' ? 'EU' : code.slice(0, 2);
    const a = cc.charCodeAt(0); const b = cc.charCodeAt(1);
    if (a < 65 || a > 90 || b < 65 || b > 90) return '';
    return String.fromCodePoint(0x1F1E6 + a - 65, 0x1F1E6 + b - 65);
  }

  // ── LocalStorage helpers (currency persistence) ──────────────────────────

  private readStoredCurrency(): string {
    const v = localStorage.getItem(CURRENCY_STORAGE_KEY);
    return v && v.trim().length === 3 ? v.trim().toUpperCase() : 'USD';
  }

  private writeStoredCurrency(code: string): void {
    localStorage.setItem(CURRENCY_STORAGE_KEY, code.toUpperCase());
  }
}
