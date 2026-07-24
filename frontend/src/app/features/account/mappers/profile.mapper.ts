import type { ProfileDto } from '../models/profile.dto';
import type { ProfileViewModel } from '../models/profile.model';
import { ROLE_LABELS } from '../models/profile.model';

export function mapProfileDtoToViewModel(dto: ProfileDto): ProfileViewModel {
  return {
    userId: dto.user_id,
    username: dto.username,
    email: dto.email,
    displayName: dto.display_name || dto.username,
    primaryRole: dto.primary_role,
    primaryRoleId: dto.primary_role_id || '',
    primaryRoleLabel: ROLE_LABELS[dto.primary_role] || dto.primary_role,
    isActive: dto.is_active,
    createdAt: dto.created_at,

    phone: dto.phone || '',
    notificationEmail: dto.notification_email || '',

    addressStreet: dto.address_street || '',
    addressCity: dto.address_city || '',
    addressState: dto.address_state || '',
    addressCountry: dto.address_country || '',
    addressPostalCode: dto.address_postal_code || '',

    dateOfBirth: dto.date_of_birth || '',
    nationality: dto.nationality || '',
    idDocumentType: dto.id_document_type || '',
    idDocumentNumber: dto.id_document_number || '',

    preferredLanguage: dto.preferred_language || 'es',
    marketingOptIn: dto.marketing_opt_in ?? false,
    notificationEmailEnabled: dto.notification_email_enabled ?? true,
    notificationSmsEnabled: dto.notification_sms_enabled ?? false,

    avatarUrl: dto.avatar_url || '',

    socialInstagram: dto.social_instagram || '',
    socialFacebook: dto.social_facebook || '',
    socialTwitter: dto.social_twitter || '',
    socialLinkedin: dto.social_linkedin || '',

    travelPurpose: dto.travel_purpose || '',
    travelBudget: dto.travel_budget || '',
    travelCompanions: dto.travel_companions || '',
    travelAccommodation: dto.travel_accommodation || '',
    travelDestinationType: dto.travel_destination_type || '',
    travelInterests: dto.travel_interests || '',
    travelFrequentFlyer: dto.travel_frequent_flyer || '',
    travelLoyaltyPrograms: dto.travel_loyalty_programs || '',
    travelNotes: dto.travel_notes || '',
  };
}
