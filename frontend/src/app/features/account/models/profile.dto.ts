export interface ProfileDto {
  user_id: string;
  username: string;
  email: string;
  display_name: string;
  primary_role_id?: string;
  primary_role: string;
  is_active: boolean;
  created_at: string;

  // Core profile
  phone: string;
  notification_email: string;
  address_street: string;
  address_city: string;
  address_state: string;
  address_country: string;
  address_postal_code: string;
  date_of_birth: string;
  nationality: string;
  id_document_type: string;
  id_document_number: string;
  preferred_language: string;
  marketing_opt_in: boolean;
  notification_email_enabled: boolean;
  notification_sms_enabled: boolean;

  // Avatar
  avatar_url: string;

  // Social media
  social_instagram: string;
  social_facebook: string;
  social_twitter: string;
  social_linkedin: string;

  // Travel preferences
  travel_purpose: string;
  travel_budget: string;
  travel_companions: string;
  travel_accommodation: string;
  travel_destination_type: string;
  travel_interests: string;
  travel_frequent_flyer: string;
  travel_loyalty_programs: string;
  travel_notes: string;
}

export interface ProfileUpdatePayload {
  display_name?: string;
  phone?: string;
  notification_email?: string;
  address_street?: string;
  address_city?: string;
  address_state?: string;
  address_country?: string;
  address_postal_code?: string;
  date_of_birth?: string;
  nationality?: string;
  id_document_type?: string;
  id_document_number?: string;
  preferred_language?: string;
  marketing_opt_in?: boolean;
  notification_email_enabled?: boolean;
  notification_sms_enabled?: boolean;
  avatar_url?: string;
  social_instagram?: string;
  social_facebook?: string;
  social_twitter?: string;
  social_linkedin?: string;
  travel_purpose?: string;
  travel_budget?: string;
  travel_companions?: string;
  travel_accommodation?: string;
  travel_destination_type?: string;
  travel_interests?: string;
  travel_frequent_flyer?: string;
  travel_loyalty_programs?: string;
  travel_notes?: string;
}
