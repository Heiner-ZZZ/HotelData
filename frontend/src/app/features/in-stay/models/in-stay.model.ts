export interface StaySession {
  token: string;
  booking_id: string;
  prop_id: number;
  room_label: string;
  guest_name: string;
  check_in: string;
  check_out: string;
  created_at: string;
  expires_at: string | null;
  active: boolean;
}

export interface CompendiumInfo {
  hotel_name: string;
  hotel_address: string;
  hotel_phone: string;
  wifi_ssid: string;
  wifi_password: string;
  check_in_time: string;
  check_out_time: string;
  breakfast_hours: string;
  restaurant_hours: string;
  gym_hours: string;
  pool_hours: string;
  parking_info: string;
  emergency_contact: string;
  policies: { title?: string; description?: string; cancellation_policy?: string }[];
  amenities: { name: string; icon?: string }[];
}

export interface FolioPosting {
  concept: string;
  category: string;
  amount: number;
  type: string;
  posted_at: string;
}

export interface PortalData {
  session: StaySession;
  compendium: CompendiumInfo;
  charges: AdditionalCharge[];
  folio_balance: number;
  folio_postings: FolioPosting[];
  nights_remaining: number;
  dnd_active: boolean;
  unread_messages: number;
  pending_requests: number;
}

export interface AdditionalCharge {
  concept: string;
  amount: number;
  quantity: number;
  total: number;
  category: string;
  note: string;
  created_at: string;
}

export interface ChatMessage {
  _id: string;
  booking_id: string;
  prop_id: number;
  room_label: string;
  sender: 'guest' | 'staff';
  staff_name: string;
  message: string;
  created_at: string;
  read: boolean;
}

export interface ServiceRequest {
  _id: string;
  booking_id: string;
  prop_id: number;
  room_label: string;
  request_type: string;
  request_type_label: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  status_label: string;
  staff_response: string;
  created_at: string;
  resolved_at: string | null;
}

export interface LostItem {
  _id: string;
  prop_id: number;
  booking_id: string;
  guest_name: string;
  guest_contact: string;
  item_name: string;
  description: string;
  found_location: string;
  found_by: string;
  status: string;
  notes: string;
  returned_to: string;
  returned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  _id: string; // room_label
  booking_id: string;
  prop_id: number;
  guest_name: string;
  last_message: string;
  last_sender: string;
  last_time: string;
  message_count: number;
  unread: number;
  dnd: boolean;
}
