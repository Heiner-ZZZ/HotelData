import type { HotelCompareItem } from '../../models/hotel-compare.model';
import {
  hotelGalleryImages,
  isValidImageUrl,
} from '../../../../shared/utils/placeholder-image.util';

/** Map amenity keywords to Material Symbols icons. */
export const AMENITY_ICONS: Record<string, string> = {
  wifi: 'wifi',
  'wi-fi': 'wifi',
  internet: 'wifi',
  piscina: 'pool',
  pool: 'pool',
  alberca: 'pool',
  desayuno: 'breakfast_dining',
  breakfast: 'breakfast_dining',
  restaurante: 'restaurant',
  restaurant: 'restaurant',
  gym: 'fitness_center',
  gimnasio: 'fitness_center',
  'estacionamiento': 'local_parking',
  parking: 'local_parking',
  'aire acondicionado': 'ac_unit',
  ac: 'ac_unit',
  'air conditioning': 'ac_unit',
  'tv': 'tv',
  television: 'tv',
  'bar': 'local_bar',
  'spa': 'spa',
  'lavandería': 'local_laundry_service',
  laundry: 'local_laundry_service',
  'transporte': 'airport_shuttle',
  shuttle: 'airport_shuttle',
  'negocios': 'business_center',
  'business center': 'business_center',
  'mascotas': 'pets',
  pets: 'pets',
  'pet': 'pets',
  'vista': 'visibility',
  view: 'visibility',
  'terraza': 'deck',
  terrace: 'deck',
  'jardín': 'grass',
  garden: 'grass',
  'playa': 'beach_access',
  beach: 'beach_access',
  'mar': 'beach_access',
  'montaña': 'terrain',
  mountain: 'terrain',
  'recepción': 'concierge',
  'front desk': 'concierge',
  'seguridad': 'security',
  security: 'security',
  'ascensor': 'elevator',
  elevator: 'elevator',
  'calefacción': 'mode_heat',
  heating: 'mode_heat',
  'cocina': 'kitchen',
  kitchen: 'kitchen',
  'microondas': 'microwave',
  microwave: 'microwave',
  'refrigerador': 'kitchen',
  fridge: 'kitchen',
  'cafetera': 'coffee',
  coffee: 'coffee',
  'agua': 'water_drop',
  water: 'water_drop',
  'toallas': 'bathtub',
  towels: 'bathtub',
  'secador': 'air',
  'hair dryer': 'air',
  'plancha': 'iron',
  iron: 'iron',
  'caja fuerte': 'lock',
  safe: 'lock',
  'teléfono': 'phone_in_talk',
  phone: 'phone_in_talk',
  'adaptador': 'power',
  adapter: 'power',
  'universal': 'power',
  'enchufe': 'power',
  outlet: 'power',
  'escritorio': 'desk',
  desk: 'desk',
  'silla': 'chair',
  chair: 'chair',
  'balcón': 'balcony',
  balcony: 'balcony',
  'hamaca': 'deck',
  'sombrilla': 'umbrella',
  umbrella: 'umbrella',
  'quemador': 'outdoor_grill',
  grill: 'outdoor_grill',
  'fogata': 'local_fire_department',
  fireplace: 'local_fire_department',
};

/** Amenity category definitions with color themes (Expedia/Booking.com style). */
export const AMENITY_CATEGORIES: Record<string, { keywords: string[]; color: string; bgColor: string; icon: string; label: string }> = {
  conectividad: {
    keywords: ['wifi', 'wi-fi', 'internet'],
    color: '#1463ff',
    bgColor: 'rgba(20, 99, 255, 0.1)',
    icon: 'wifi',
    label: 'Conectividad',
  },
  piscina: {
    keywords: ['piscina', 'pool', 'alberca'],
    color: '#0d9488',
    bgColor: 'rgba(13, 148, 136, 0.1)',
    icon: 'pool',
    label: 'Piscina',
  },
  comida: {
    keywords: ['desayuno', 'breakfast', 'restaurante', 'restaurant', 'bar', 'cafetera', 'coffee'],
    color: '#d97706',
    bgColor: 'rgba(217, 119, 6, 0.1)',
    icon: 'breakfast_dining',
    label: 'Comida y bebida',
  },
  wellness: {
    keywords: ['spa', 'gym', 'gimnasio', 'fitness', 'sauna', 'masaje', 'bañera', 'hidromasaje', 'jaccuzi'],
    color: '#7c3aed',
    bgColor: 'rgba(124, 58, 237, 0.1)',
    icon: 'spa',
    label: 'Wellness',
  },
  transporte: {
    keywords: ['estacionamiento', 'parking', 'transporte', 'shuttle', 'airport', 'traslado'],
    color: '#059669',
    bgColor: 'rgba(5, 150, 105, 0.1)',
    icon: 'local_parking',
    label: 'Transporte',
  },
  habitacion: {
    keywords: ['aire acondicionado', 'ac', 'air conditioning', 'tv', 'television', 'calefacción', 'heating', 'cocina', 'kitchen', 'microondas', 'refrigerador', 'fridge', 'caja fuerte', 'safe', 'escritorio', 'desk', 'plancha', 'iron', 'secador', 'hair dryer', 'toallas', 'towels', 'agua', 'water', 'cafetera', 'coffee'],
    color: '#1463ff',
    bgColor: 'rgba(20, 99, 255, 0.1)',
    icon: 'ac_unit',
    label: 'En la habitación',
  },
  exterior: {
    keywords: ['vista', 'view', 'terraza', 'terrace', 'balcón', 'balcony', 'jardín', 'garden', 'playa', 'beach', 'mar', 'montaña', 'mountain', 'hamaca', 'sombrilla', 'umbrella', 'quemador', 'grill', 'fogata', 'fireplace'],
    color: '#0f8a60',
    bgColor: 'rgba(15, 138, 96, 0.1)',
    icon: 'deck',
    label: 'Exteriores',
  },
  servicios: {
    keywords: ['recepción', 'front desk', 'concierge', 'seguridad', 'security', 'ascensor', 'elevator', 'lavandería', 'laundry', 'negocios', 'business center', 'mascotas', 'pets', 'pet', 'teléfono', 'phone', 'adaptador', 'adapter', 'universal', 'enchufe', 'outlet', 'caja fuerte', 'safe'],
    color: '#6b7280',
    bgColor: 'rgba(107, 114, 128, 0.1)',
    icon: 'concierge',
    label: 'Servicios',
  },
};

/** Map an amenity name to its closest Material Symbols icon. */
export function amenityIcon(amenity: string): string {
  const key = amenity.toLowerCase().trim();
  return AMENITY_ICONS[key] || 'check_circle';
}

/** Map a policy label to its Material Symbols icon. */
export function policyIcon(label: string): string {
  const icons: Record<string, string> = {
    'Check-in': 'login',
    'Check-out': 'logout',
    'Mascotas': 'pets',
    'Niños': 'child_care',
    'Camas extra': 'bed',
    'Pagos': 'payments',
    'Reglas': 'gavel',
  };
  return icons[label] || 'info';
}

/** Parse comma-separated amenity text into a clean list. */
export function amenityList(text: string | undefined | null): string[] {
  if (!text) return [];
  return text.split(',').map((t) => t.trim()).filter(Boolean);
}

/** Categorize amenities by type with color themes (Expedia/Booking.com style). */
export function categorizeAmenities(text: string | undefined | null): { category: string; label: string; color: string; bgColor: string; icon: string; amenities: string[] }[] {
  const items = amenityList(text);
  if (!items.length) return [];

  const categorized: Record<string, string[]> = {};
  const uncategorized: string[] = [];

  for (const amenity of items) {
    let matched = false;
    for (const [catKey, catDef] of Object.entries(AMENITY_CATEGORIES)) {
      for (const keyword of catDef.keywords) {
        if (amenity.toLowerCase().includes(keyword.toLowerCase())) {
          if (!categorized[catKey]) categorized[catKey] = [];
          categorized[catKey].push(amenity);
          matched = true;
          break;
        }
      }
      if (matched) break;
    }
    if (!matched) {
      uncategorized.push(amenity);
    }
  }

  const result: { category: string; label: string; color: string; bgColor: string; icon: string; amenities: string[] }[] = [];
  for (const [catKey, catDef] of Object.entries(AMENITY_CATEGORIES)) {
    if (categorized[catKey]?.length) {
      result.push({
        category: catKey,
        label: catDef.label,
        color: catDef.color,
        bgColor: catDef.bgColor,
        icon: catDef.icon,
        amenities: categorized[catKey],
      });
    }
  }
  if (uncategorized.length) {
    result.push({
      category: 'otros',
      label: 'Otros',
      color: '#6b7280',
      bgColor: 'rgba(107, 114, 128, 0.1)',
      icon: 'check_circle',
      amenities: uncategorized,
    });
  }
  return result;
}

/** Get the minimum nightly rate across compared hotels as a display string. */
export function minRate(items: HotelCompareItem[]): string {
  if (!items?.length) return '—';
  const item = items.find((i) => i.minNightlyRateLabel);
  return item?.minNightlyRateLabel || '—';
}

/** Galería centralizada — mismo `hotelGalleryImages` que `/welcome` y `/search` (4 fotos). */
export function carouselImages(hotel: HotelCompareItem): string[] {
  const seed = hotel.propId || 0;
  const placeholders = hotelGalleryImages(seed, null, 4, 800, 400);
  if (isValidImageUrl(hotel.imageUrl)) {
    return [hotel.imageUrl as string, ...placeholders.slice(1)];
  }
  return placeholders;
}

/** Compute comparison flags for each hotel vs average. */
export function computeComparisonFlags(items: HotelCompareItem[]): Map<number, import('../../models/hotel-compare.model').ComparisonFlags> {
  if (!items?.length) return new Map();

  const n = items.length;
  const hasPrice = items.filter((i) => i.minNightlyRate != null);
  const avgPrice = hasPrice.length ? hasPrice.reduce((s, i) => s + i.minNightlyRate!, 0) / hasPrice.length : 0;
  const avgScore = items.reduce((s, i) => s + (i.propReviewScore ?? 0), 0) / n;
  const avgStars = items.reduce((s, i) => s + (i.propStarrating ?? 0), 0) / n;
  const avgRoomTypes = items.reduce((s, i) => s + i.roomTypes.length, 0) / n;

  const map = new Map<number, import('../../models/hotel-compare.model').ComparisonFlags>();
  for (const item of items) {
    map.set(item.propId, {
      betterPrice: item.minNightlyRate != null && item.minNightlyRate < avgPrice,
      betterScore: item.propReviewScore != null && item.propReviewScore > avgScore,
      betterStars: item.propStarrating != null && item.propStarrating > avgStars,
      betterRoomTypes: item.roomTypes.length > avgRoomTypes,
    });
  }
  return map;
}
