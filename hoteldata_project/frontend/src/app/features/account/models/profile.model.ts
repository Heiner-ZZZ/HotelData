export interface ProfileViewModel {
  userId: string;
  username: string;
  email: string;
  displayName: string;
  primaryRole: string;
  primaryRoleLabel: string;
  isActive: boolean;
  createdAt: string;

  // Contact
  phone: string;
  notificationEmail: string;

  // Address
  addressStreet: string;
  addressCity: string;
  addressState: string;
  addressCountry: string;
  addressPostalCode: string;

  // Personal / Identity
  dateOfBirth: string;
  nationality: string;
  idDocumentType: string;
  idDocumentNumber: string;

  // Preferences
  preferredLanguage: string;
  marketingOptIn: boolean;
  notificationEmailEnabled: boolean;
  notificationSmsEnabled: boolean;

  // Avatar
  avatarUrl: string;

  // Social media
  socialInstagram: string;
  socialFacebook: string;
  socialTwitter: string;
  socialLinkedin: string;

  // Travel preferences
  travelPurpose: string;
  travelBudget: string;
  travelCompanions: string;
  travelAccommodation: string;
  travelDestinationType: string;
  travelInterests: string;
  travelFrequentFlyer: string;
  travelLoyaltyPrograms: string;
  travelNotes: string;
}

export const ROLE_LABELS: Record<string, string> = {
  super_admin: 'Super Administrador',
  admin_sistema: 'Admin. Sistema',
  hotel_partner: 'Hotel Partner',
  gerente_hotel: 'Gerente de Hotel',
  revenue_manager: 'Revenue Manager',
  marketing_hotelero: 'Marketing Hotelero',
  auditor_datos: 'Auditor de Datos',
  operador_datos: 'Operador de Datos',
  cliente: 'Cliente / Viajero',
};

export const LANGUAGE_OPTIONS = [
  { value: 'es', label: 'Español' },
  { value: 'en', label: 'English' },
  { value: 'pt', label: 'Português' },
  { value: 'fr', label: 'Français' },
];

export const DOCUMENT_TYPES = [
  { value: '', label: 'Seleccionar…' },
  { value: 'passport', label: 'Pasaporte' },
  { value: 'dni', label: 'DNI / Cédula' },
  { value: 'driver_license', label: 'Licencia de conducir' },
  { value: 'id_card', label: 'Tarjeta de identidad' },
  { value: 'other', label: 'Otro documento' },
];

export interface SelectOption {
  value: string;
  label: string;
  icon?: string;
}

export const TRAVEL_PURPOSE_OPTIONS: SelectOption[] = [
  { value: '', label: 'Seleccionar…' },
  { value: 'placer', label: 'Placer / Vacaciones', icon: 'beach_access' },
  { value: 'negocio', label: 'Negocios / Trabajo', icon: 'work' },
  { value: 'familiar', label: 'Visita familiar', icon: 'family_restroom' },
  { value: 'aventura', label: 'Aventura', icon: 'hiking' },
  { value: 'romantico', label: 'Escapada romántica', icon: 'favorite' },
  { value: 'salud', label: 'Salud / Bienestar', icon: 'spa' },
  { value: 'cultural', label: 'Cultural / Educativo', icon: 'museum' },
  { value: 'mixed', label: 'Mixto / Varios', icon: 'sync_alt' },
];

export const TRAVEL_BUDGET_OPTIONS: SelectOption[] = [
  { value: '', label: 'Seleccionar…' },
  { value: 'economico', label: 'Económico', icon: 'savings' },
  { value: 'moderado', label: 'Moderado', icon: 'account_balance_wallet' },
  { value: 'premium', label: 'Premium', icon: 'workspace_premium' },
  { value: 'lujo', label: 'Lujo', icon: 'diamond' },
];

export const TRAVEL_COMPANIONS_OPTIONS: SelectOption[] = [
  { value: '', label: 'Seleccionar…' },
  { value: 'solo', label: 'Solo', icon: 'person' },
  { value: 'pareja', label: 'En pareja', icon: 'favorite' },
  { value: 'familia', label: 'En familia', icon: 'family_restroom' },
  { value: 'grupo', label: 'Grupo de amigos', icon: 'diversity_3' },
  { value: 'colegas', label: 'Colegas de trabajo', icon: 'work' },
];

export const TRAVEL_ACCOMMODATION_OPTIONS: SelectOption[] = [
  { value: '', label: 'Seleccionar…' },
  { value: 'hotel', label: 'Hotel', icon: 'hotel' },
  { value: 'resort', label: 'Resort', icon: 'pool' },
  { value: 'hostel', label: 'Hostel / Albergue', icon: 'backpack' },
  { value: 'boutique', label: 'Hotel boutique', icon: 'star' },
  { value: 'apartamento', label: 'Apartamento', icon: 'apartment' },
  { value: 'cabaña', label: 'Cabaña / Eco-lodge', icon: 'forest' },
];

export const TRAVEL_DESTINATION_OPTIONS: SelectOption[] = [
  { value: '', label: 'Seleccionar…' },
  { value: 'playa', label: 'Playa', icon: 'beach_access' },
  { value: 'montaña', label: 'Montaña', icon: 'terrain' },
  { value: 'ciudad', label: 'Ciudad', icon: 'location_city' },
  { value: 'rural', label: 'Rural / Campo', icon: 'agriculture' },
  { value: 'aventura', label: 'Aventura / Naturaleza', icon: 'hiking' },
  { value: 'cultura', label: 'Cultural / Histórico', icon: 'museum' },
];
