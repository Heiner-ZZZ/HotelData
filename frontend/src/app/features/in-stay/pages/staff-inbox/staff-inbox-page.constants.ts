import type { CategoryChip } from './staff-inbox-page.types';

export const REQUEST_CATEGORIES: readonly CategoryChip[] = [
  { id: 'concierge', icon: 'local_activity', label: 'Concierge' },
  { id: 'housekeeping', icon: 'cleaning_services', label: 'Housekeeping' },
  { id: 'room_service', icon: 'room_service', label: 'Room Service' },
  { id: 'maintenance', icon: 'handyman', label: 'Technical' },
] as const;
