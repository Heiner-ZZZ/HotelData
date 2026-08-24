import { CurrencyPipe } from '@angular/common';
import { httpResource, HttpResourceRef } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ProductsAuthService } from '../../services/products-auth.service';
import { ReportApiService } from '../../services/report-api.service';
import { ProductsSectionNavComponent } from '../products-section-nav/products-section-nav';
import type { MarginReportDto } from '../../models/products-report.dto';

@Component({
  selector: 'app-margin-report',
  standalone: true,
  imports: [
    CurrencyPipe,
    FormsModule,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    ProductsSectionNavComponent,
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

  readonly canSeeCost = this.productsAuth.canSeeCost;

  /** Report-wide search filter. */
  readonly searchTerm = signal('');

  readonly report: HttpResourceRef<MarginReportDto | undefined>;

  /** Filtered items by search term. */
  readonly filteredItems = computed(() => {
    const data = this.report.value();
    if (!data) return [];
    const term = this.searchTerm().trim().toLowerCase();
    if (!term) return data.items;
    return data.items.filter((item) => {
      const haystack = `${item.name} ${item.category} ${item.product_id}`.toLowerCase();
      return haystack.includes(term);
    });
  });

  constructor() {
    this.report = this.api.marginReport(this.propId);
  }

  onSearchInput(value: string): void {
    this.searchTerm.set(value);
  }

  formatPct(pct: number): string {
    return `${pct.toFixed(1)}%`;
  }

  barWidth(pct: number): number {
    if (pct < 0) return 0;
    if (pct > 100) return 100;
    return pct;
  }

  isNegativeMargin(pct: number): boolean {
    return pct < 0;
  }
}
