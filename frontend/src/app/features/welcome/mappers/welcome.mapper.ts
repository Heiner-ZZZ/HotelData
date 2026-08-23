import type { FeaturedHotel } from '../models/welcome.models';
import { placeholderImageUrl } from '../../../shared/utils/placeholder-image.util';

/** Raw DTO shape from /api/hotels/availability. */
interface FeaturedHotelDto {
  prop_id: number;
  display_name: string;
  prop_starrating: number | null;
  prop_review_score: number | null;
  image_url: string | null;
  destination_labels: string[];
  min_nightly_rate_label: string | null;
}

/** Generates a deterministic placeholder image URL (loremflickr.com seeded by hotel id). */
export function hotelImageUrl(propId: number, variant: 'hotel' | 'lobby' | 'pool' = 'hotel'): string {
  return placeholderImageUrl(`${propId}-${variant}`, 400, 250);
}

/** Variantes que forman la mini-galería de cada card destacada. */
const WELCOME_GALLERY_VARIANTS = ['hotel', 'lobby', 'pool'] as const;

/** Maps the raw availability API response to FeaturedHotel cards. */
export function mapFeaturedHotels(raw: { items?: FeaturedHotelDto[] }): FeaturedHotel[] {
  return (raw.items ?? []).map((h) => ({
    id: h.prop_id,
    name: h.display_name,
    location: (h.destination_labels ?? [])[0] ?? '',
    stars: h.prop_starrating ?? 0,
    score: h.prop_review_score,
    images: WELCOME_GALLERY_VARIANTS.map((variant) => hotelImageUrl(h.prop_id, variant)),
    rateLabel: h.min_nightly_rate_label,
  }));
}

/** Converts an ISO currency code (USD, MXN, EUR...) to a flag emoji. */
export function currencyFlag(code: string): string {
  const cc = code === 'EUR' ? 'EU' : code.slice(0, 2);
  const a = cc.charCodeAt(0);
  const b = cc.charCodeAt(1);
  if (a < 65 || a > 90 || b < 65 || b > 90) return '';
  return String.fromCodePoint(0x1f1e6 + a - 65, 0x1f1e6 + b - 65);
}
