import { CurrencyPipe } from '@angular/common';
import { httpResource, HttpResourceRef } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ProductsAuthService } from '../../services/products-auth.service';
import { ReportApiService } from '../../services/report-api.service';
import type { MarginReportDto } from '../../models/products-report.dto';

@Component({
  selector: 'app-margin-report',
  standalone: true,
  imports: [
    CurrencyPipe,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
  ],
  templateUrl: './margin-report.html',
  styleUrl: './margin-report.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export default class MarginReportComponent {
  private readonly api = inject(ReportApiService);
  private readonly propCtx = inject(PropertyContextService);
  private readonly productsAuth = inject(ProductsAuthService);

  readonly propId = computed(() => this.propCtx.currentPropId());

  /** Permission gate (forwarded to ProductsAuthService). */
  readonly canSeeCost = this.productsAuth.canSeeCost;

  readonly report: HttpResourceRef<MarginReportDto | undefined>;

  constructor() {
    this.report = this.api.marginReport(this.propId);
  }

  formatPct(pct: number): string {
    return `${pct.toFixed(1)}%`;
  }

  /** Clamp visual bar width between 0 and 100. */  /** Clamp a percentage into [0, 100] for visual bar widths. */
  barWidth(pct: number): number {
    if (pct < 0) return 0;
    if (pct > 100) return 100;
    return pct;
  }

  isNegativeMargin(pct: number): boolean {
    return pct < 0;
  }
}
