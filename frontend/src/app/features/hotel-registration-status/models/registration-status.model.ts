/** Modelo tipado de la pantalla del dueño pendiente (UX-3). */
import type { ApprovalStatusDto } from './registration-status.dto';

export type ApprovalStatus = ApprovalStatusDto;

export interface RegistrationStatus {
  approvalStatus: ApprovalStatus;
  rejectedReason: string | null;
  feedback: string | null;
  submittedAt: string | null;
  statusChangedAt: string | null;
  property: RegistrationProperty;
  suggestedBand: SuggestedBand | null;
  /** Gracia inicial de la primera factura (días tras la aprobación). */
  initialGraceDays: number;
  /** Métodos de pago manuales del catálogo (sin pasarela bancaria). */
  paymentMethods: PaymentMethod[];
  timeline: TimelineEvent[];
}

export interface PaymentMethod {
  code: string;
  label: string;
  sortOrder: number;
  details: Record<string, string>;
}

export interface RegistrationProperty {
  name: string;
  type: string;
  city: string;
  country: string;
  totalRooms: number;
  currency: string;
  contactPhone: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
}

export interface SuggestedBand {
  band: number;
  label: string;
  monthlyUsd: number;
  /** Cuota mensual equivalente pagando el año por adelantado (~22–27% off). */
  annualMonthlyUsd: number;
  minRooms: number;
  maxRooms: number;
}

export interface TimelineEvent {
  event: string;
  at: string | null;
  detail: string;
}

/** Opciones de tipo de propiedad (mismas que el wizard de onboarding). */
export interface PropertyTypeOption {
  value: string;
  label: string;
  icon: string;
}

export const PROPERTY_TYPES: readonly PropertyTypeOption[] = [
  { value: 'hotel', label: 'Hotel', icon: 'hotel' },
  { value: 'hostal', label: 'Hostal', icon: 'hostel' },
  { value: 'apartamento', label: 'Apartamento', icon: 'apartment' },
  { value: 'bed_breakfast', label: 'Bed & Breakfast', icon: 'breakfast_dining' },
  { value: 'resort', label: 'Resort', icon: 'beach_access' },
  { value: 'cabaña', label: 'Cabaña', icon: 'cabin' },
  { value: 'boutique', label: 'Boutique', icon: 'diamond' },
];

const PROPERTY_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  PROPERTY_TYPES.map((t) => [t.value, t.label]),
);

export function propertyTypeLabel(value: string): string {
  return PROPERTY_TYPE_LABELS[value] ?? value;
}
