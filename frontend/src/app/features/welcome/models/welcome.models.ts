/** Featured hotel card shown on the welcome landing. */
export interface FeaturedHotel {
  readonly id: number;
  readonly name: string;
  readonly location: string;
  readonly stars: number | null;
  readonly score: number | null;
  readonly imageUrl: string;
  readonly rateLabel: string | null;
}

export interface WelcomeCategory {
  readonly key: string;
  readonly label: string;
  readonly icon: string;
}

/** Shape of a row in the `system_currencies` collection (MongoDB). */
export interface SystemCurrencyDto {
  readonly code: string;
  readonly name: string;
  readonly symbol: string;
  readonly decimals: number;
  readonly active: boolean;
}

/**
 * Single-tab category list. Hoisted to module scope as a placeholder so
 * a future dev restoring multi-tab navigation has one source of truth for
 * the data.
 */
export const CATEGORIES: readonly WelcomeCategory[] = [
  { key: 'hotels', label: 'Hoteles', icon: 'hotel' },
];

export const CURRENCY_STORAGE_KEY = 'hoteldata.preferred_currency';

export const FALLBACK_CURRENCIES: readonly SystemCurrencyDto[] = [
  { code: 'USD', name: 'Dólar estadounidense', symbol: '$', decimals: 2, active: true },
  { code: 'MXN', name: 'Peso mexicano',         symbol: '$', decimals: 2, active: true },
  { code: 'EUR', name: 'Euro',                  symbol: '€', decimals: 2, active: true },
  { code: 'COP', name: 'Peso colombiano',       symbol: '$', decimals: 0, active: true },
];
