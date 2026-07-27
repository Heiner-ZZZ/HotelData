/**
 * Angular 22 `httpResource`-based API service for the 3 product reports.
 *
 * Usage in components:
 *
 *   private api = inject(ReportApiService);
 *
 *   // In some page/partial component constructor or computed:
 *   report = httpResource<MarginReportDto>(() => ({
 *     url: this.api.marginReportUrl(this.propId) ?? '',
 *   }));
 *
 * The `inject(ReportApiService)` pattern keeps the service singleton while
 * letting each component pick the right endpoint. The service caches its
 * `baseUrl` from API_CONFIG.
 */

import { HttpClient } from '@angular/common/http';
import { httpResource, HttpResourceRef } from '@angular/common/http';
import { inject, Injectable, Signal } from '@angular/core';

import { API_CONFIG } from '../../../core/api/api.config';
import type {
  CogsMethod,
  CogsReportDto,
  CogsReportItemDto,
  CogsSummaryDto,
  LayerBreakdownDto,
  MarginReportDto,
  MarginReportItemDto,
  MarginSummaryDto,
  StockCategorySummaryDto,
  StockValueReportDto,
  StockValueReportPeriod,
  StockValueSummaryDto,
  StockValueItemDto,
} from '../models/products-report.dto';

@Injectable({ providedIn: 'root' })
export class ReportApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly base = `${this.apiConfig.baseUrl}/management/products/reports`;

  // ─── URL builders (consumed by httpResource) ──────────────────────────

  /** URL for the margin report for a given property. */
  marginReportUrl(propId: Signal<number | null | undefined>): string | undefined {
    const pid = propId();
    return pid ? `${this.base}/margin?prop_id=${pid}` : undefined;
  }

  /** URL for the COGS report with the given period + layer drain method (Fase 6). */
  cogsReportUrl(
    propId: Signal<number | null | undefined>,
    period: Signal<StockValueReportPeriod>,
    method: Signal<CogsMethod>,
  ): string | undefined {
    const pid = propId();
    const p = period();
    const m = method();
    return pid ? `${this.base}/cogs?prop_id=${pid}&period=${p}&method=${m}` : undefined;
  }

  /** URL for the stock-value report for a given property. */
  stockValueReportUrl(propId: Signal<number | null | undefined>): string | undefined {
    const pid = propId();
    return pid ? `${this.base}/stock-value?prop_id=${pid}` : undefined;
  }

  // ─── httpResource factories (for components that prefer explicit data) ─

  marginReport(propId: Signal<number | null | undefined>): HttpResourceRef<MarginReportDto | undefined> {
    return httpResource<MarginReportDto>(() => ({ url: this.marginReportUrl(propId) ?? '' }));
  }

  cogsReport(
    propId: Signal<number | null | undefined>,
    period: Signal<StockValueReportPeriod>,
    method: Signal<CogsMethod>,
  ): HttpResourceRef<CogsReportDto | undefined> {
    return httpResource<CogsReportDto>(() => ({
      url: this.cogsReportUrl(propId, period, method) ?? '',
    }));
  }

  stockValueReport(propId: Signal<number | null | undefined>): HttpResourceRef<StockValueReportDto | undefined> {
    return httpResource<StockValueReportDto>(() => ({ url: this.stockValueReportUrl(propId) ?? '' }));
  }
}
