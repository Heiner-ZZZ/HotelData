import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface CampaignRow {
  campaignId: string;
  name: string;
  description: string;
  discountPercent: number;
  isActive: boolean;
  startDate: string;
  endDate: string;
  couponTotal: number;
  couponUsed: number;
  couponAvailable: number;
}

export interface CouponRow {
  code: string;
  activeLabel: string;
}

@Component({
  selector: 'app-promotions-table',
  imports: [],
  templateUrl: './promotions-table.html',
  styleUrl: './promotions-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PromotionsTableComponent {
  readonly campaigns = input<CampaignRow[]>([]);
  readonly coupons = input<CouponRow[]>([]);
  readonly editPromo = output<CampaignRow>();
  readonly deletePromo = output<string>();
  readonly togglePromo = output<string>();
}
