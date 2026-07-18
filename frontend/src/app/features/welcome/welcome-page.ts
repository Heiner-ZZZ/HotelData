import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal
} from '@angular/core';
import { httpResource } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { PropertyContextService } from '../../shared/services/property-context.service';
import { PropertyCurrencyPipe } from '../../shared/pipes/property-currency.pipe';
import { API_CONFIG } from '../../core/api/api.config';

interface WelcomeCategory {
  readonly key: string;
  readonly label: string;
  readonly icon: string;
}

interface WelcomeFeature {
  readonly icon: string;
  readonly title: string;
  readonly description: string;
}

/** Shape of a row in the `system_currencies` collection (MongoDB). */
interface SystemCurrencyDto {
  readonly code: string;
  readonly name: string;
  readonly symbol: string;
  readonly decimals: number;
  readonly active: boolean;
}

/** Synthetic preview tiles shown in /welcome — uses selected currency. */
interface PreviewReservation {
  readonly id: string;
  readonly hotelName: string;
  readonly city: string;
  readonly basePriceUsd: number;
  readonly status: 'confirmed' | 'pending' | 'checked_in';
  readonly checkIn: string;
}

const PREVIEW_RESERVATIONS: readonly PreviewReservation[] = [
  {
    id: 'rsv-001',
    hotelName: 'Hotel Lima Centro',
    city: 'Lima, PE',
    basePriceUsd: 120,
    status: 'confirmed',
    checkIn: '15 nov 2026'
  },
  {
    id: 'rsv-002',
    hotelName: 'Resort Cancún Playa',
    city: 'Cancún, MX',
    basePriceUsd: 340,
    status: 'pending',
    checkIn: '22 nov 2026'
  },
  {
    id: 'rsv-003',
    hotelName: 'Hotel Quito Histórico',
    city: 'Quito, EC',
    basePriceUsd: 95,
    status: 'checked_in',
    checkIn: '18 nov 2026'
  }
];

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
  imports: [RouterLink, PropertyCurrencyPipe],
  templateUrl: './welcome-page.html',
  styleUrls: [
    '../../../styles/_auth-shell.scss',
    './welcome-page.scss'
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class WelcomePageComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly apiConfig = inject(API_CONFIG);

  readonly year = new Date().getFullYear();

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
  readonly selectedCurrencyLabel = computed(
    () => this.selectedCurrency() || 'USD'
  );

  // ── Synthetic reservation preview (uses selected currency) ──────────────

  readonly previewReservations = PREVIEW_RESERVATIONS;
  readonly previewCurrency = this.selectedCurrency;

  constructor() {
    // Auto-redirect authenticated visitors straight to their dashboard.
    // Mirrors the pattern used in LoginPageComponent.
    effect(() => {
      if (this.hasSession()) {
        const homeHref = this.authService.authState().homeHref;
        void this.router.navigateByUrl(this.authService.resolveDefaultDestination(homeHref));
      }
    });

    // Whenever the user picks a currency on the public landing, propagate it
    // to PropertyContextService so the `propertyCurrency` pipe (used across
    // the registered-guest booking view, in-stay portal, billing, etc.)
    // formats amounts in the same currency.
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

  /** Human label for the reservation status pill on preview cards. */
  reservationStatusLabel(status: PreviewReservation['status']): string {
    switch (status) {
      case 'confirmed':  return 'Confirmada';
      case 'pending':    return 'Pendiente';
      case 'checked_in': return 'En curso';
    }
  }

  // ── Features section (unchanged from previous turns) ─────────────────────

  readonly features = signal<readonly WelcomeFeature[]>([
    {
      icon: 'event_available',
      title: 'Reservas sin fricción',
      description:
        'Disponibilidad en tiempo real, check-in express y confirmaciones automáticas en cada canal de venta.'
    },
    {
      icon: 'monitoring',
      title: 'Revenue dinámico',
      description:
        'Tarifas ajustadas por demanda, segmento y estacionalidad desde un único panel con datos vivos.'
    },
    {
      icon: 'support_agent',
      title: 'Operación centralizada',
      description:
        'Housekeeping, mantenimiento y huéspedes coordinados desde cualquier dispositivo, en cualquier turno.'
    }
  ]);

  // ── LocalStorage helpers (currency persistence) ──────────────────────────
  // /welcome is client-only (loadComponent, no SSR) and localStorage is
  // universally available in browsers we support. Direct read/write is
  // safe here — no try/catch needed.

  private readStoredCurrency(): string {
    const v = localStorage.getItem(CURRENCY_STORAGE_KEY);
    return v && v.trim().length === 3 ? v.trim().toUpperCase() : 'USD';
  }

  private writeStoredCurrency(code: string): void {
    localStorage.setItem(CURRENCY_STORAGE_KEY, code.toUpperCase());
  }
}
