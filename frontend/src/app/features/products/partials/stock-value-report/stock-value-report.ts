import { CurrencyPipe, DecimalPipe, DatePipe } from '@angular/common';
import { httpResource, HttpResourceRef } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ProductsAuthService } from '../../services/products-auth.service';
import { ReportApiService } from '../../services/report-api.service';
import type { StockValueItemDto, StockValueReportDto } from '../../models/products-report.dto';

@Component({
  selector: 'app-stock-value-report',
  standalone: true,
  imports: [
    CurrencyPipe,
    DecimalPipe,
    DatePipe,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
  ],
  templateUrl: './stock-value-report.html',
  styleUrl: './stock-value-report.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export default class StockValueReportComponent {
  private readonly api = inject(ReportApiService);
  private readonly propCtx = inject(PropertyContextService);
  private readonly productsAuth = inject(ProductsAuthService);

  readonly propId = computed(() => this.propCtx.currentPropId());

  /** Eyebrow showing report generation timestamp. Empty until first value. */
  readonly asOfEyebrow = computed<string>(() => {
    const data = this.report.value();
    if (!data?.as_of) return '';
    try {
      const d = new Date(data.as_of);
      return `Actualizado al ${d.toLocaleString('es-MX', {
        day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
      })}`;
    } catch {
      return data.as_of;
    }
  });

  readonly canSeeCost = this.productsAuth.canSeeCost;

  readonly report: HttpResourceRef<StockValueReportDto | undefined>;

  constructor() {
    this.report = this.api.stockValueReport(this.propId);
  }

  /** Width of category bar relative to total. */
  categorySharePct(value: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((value / total) * 100);
  }

  trackByProductId(_index: number, item: StockValueItemDto): string {
    return item.id;
  }
}
