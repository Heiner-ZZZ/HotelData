import { CurrencyPipe, DecimalPipe, DatePipe } from '@angular/common';
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
import type { StockValueItemDto, StockValueReportDto } from '../../models/products-report.dto';

@Component({
  selector: 'app-stock-value-report',
  standalone: true,
  imports: [
    CurrencyPipe,
    DecimalPipe,
    DatePipe,
    FormsModule,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    ProductsSectionNavComponent,
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
  readonly searchTerm = signal('');

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

  readonly rankedCategories = computed(() => {
    const cats = this.report.value()?.by_category ?? [];
    return [...cats].sort((a, b) => b.total_value - a.total_value);
  });

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
    this.report = this.api.stockValueReport(this.propId);
  }

  onSearchInput(value: string): void {
    this.searchTerm.set(value);
  }

  categorySharePct(value: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((value / total) * 100);
  }

  trackByProductId(_index: number, item: StockValueItemDto): string {
    return item.id;
  }
}
