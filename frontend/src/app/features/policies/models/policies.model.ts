export interface PolicyPropertyOption {
  propId: number;
  label: string;
}

export interface PropertyOptionsPage {
  items: PolicyPropertyOption[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}

export interface PolicySummaryItem {
  label: string;
  value: string;
  detail: string;
}

export interface PolicyRoomTypeOption {
  id: string;
  name: string;
}

export interface PoliciesViewModel {
  propId: number;
  hotelName: string;
  countryLabel: string;
  reviewLabel: string;
  avgPriceLabel: string;
  sourceCollection: string;
  checkInTime: string;
  checkOutTime: string;
  cancellationPolicy: string;
  petPolicy: string;
  childrenPolicy: string;
  extraBedPolicy: string;
  paymentPolicy: string;
  houseRules: string;
  roomTypeId: string;
  ratePlanId: string;
  // SPEC 022 structured fields
  cancellationHours: number;
  cancellationPenaltyPercent: number;
  petsAllowed: boolean;
  petFee: number;
  childrenAllowed: boolean;
  extraBedFee: number;
  minStay: number;
  maxStay: number;
  roomTypes: PolicyRoomTypeOption[];
  summary: PolicySummaryItem[];
}
