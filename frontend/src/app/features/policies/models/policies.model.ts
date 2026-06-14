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
  summary: PolicySummaryItem[];
}
