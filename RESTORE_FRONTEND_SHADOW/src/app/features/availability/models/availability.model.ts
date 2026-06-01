export interface AvailabilityPropertyOption {
  propId: number;
  label: string;
}

export interface AvailabilityRoomTypeOption {
  roomTypeId: string;
  name: string;
  capacityLabel: string;
}

export interface AvailabilityRatePlanOption {
  ratePlanId: string;
  name: string;
  baseRateLabel: string;
}

export interface AvailabilityOptions {
  propertyOptions: AvailabilityPropertyOption[];
  selectedPropId: number | null;
  roomTypeOptions: AvailabilityRoomTypeOption[];
  ratePlanOptions: AvailabilityRatePlanOption[];
}

export interface AvailabilityRow {
  date: string;
  totalRooms: number | null;
  availableRooms: number | null;
  blockedRooms: number | null;
  rateAmount: number | null;
  minStayNights: number | null;
  isClosed: boolean;
  hasBlackout: boolean;
  blackoutReason: string | null;
  blackoutBlockedRooms: number;
}

export interface AvailabilitySummary {
  days: number;
  closedDates: number;
  blackoutDates: number;
  avgRate: number | null;
  avgRateLabel: string;
}

export interface AvailabilitySnapshot {
  property: {
    propId: number;
    displayName: string;
    countryDisplayName: string;
  };
  filters: {
    propId: number;
    roomTypeId: string | null;
    ratePlanId: string | null;
    startDate: string;
    endDate: string;
  };
  options: AvailabilityOptions;
  rows: AvailabilityRow[];
  summary: AvailabilitySummary;
}

export interface AvailabilityCellChange {
  date: string;
  field:
    | 'totalRooms'
    | 'availableRooms'
    | 'blockedRooms'
    | 'rateAmount'
    | 'minStayNights'
    | 'isClosed';
  value: number | boolean | null;
}

export interface AvailabilityBulkEdit {
  startDate: string;
  endDate: string;
  totalRooms: number | null;
  availableRooms: number | null;
  blockedRooms: number | null;
  rateAmount: number | null;
  minStayNights: number | null;
  closedMode: 'keep' | 'open' | 'closed';
}
