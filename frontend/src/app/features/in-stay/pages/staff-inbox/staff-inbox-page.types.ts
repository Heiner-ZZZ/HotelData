import type { ServiceRequest } from '../../models/in-stay.model';

/** Main navigation tabs. */
export type MainTab = 'unified' | 'folios' | 'sessions' | 'lost-found';

/** Category chip definition for quick request creation + filtering. */
export interface CategoryChip {
  id: string;
  icon: string;
  label: string;
}

/** Unified timeline item (message or request). */
export interface TimelineItem {
  type: 'message' | 'request';
  id: string;
  roomLabel: string;
  guestName: string;
  preview: string;
  time: string;
  unread?: number;
  status?: string;
  statusLabel?: string;
  requestType?: string;
  request?: ServiceRequest;
}
