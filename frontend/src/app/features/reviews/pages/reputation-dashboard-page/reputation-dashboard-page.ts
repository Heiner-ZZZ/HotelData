import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal, rxResource } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { KpiChartComponent, type KpiChartDataset } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { ReportsExportService } from '../../../../shared/services/reports-export.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { REPORTS_DOWNLOAD } from '../../../../core/auth/permission.constants';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { HorizontalSubNavComponent } from '../../../../shared/ui/horizontal-sub-nav/horizontal-sub-nav';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import {
  buildReportShell,
  buildSummaryGrid,
  buildTable,
} from '../../../../shared/utils/report-html-templates';
import type { ReputationDashboard, ReviewAnalytics, ReviewAnalyticsRow } from '../../models/reviews.model';
import { ReviewsApiService } from '../../services/reviews-api.service';

/** Tamaño de página del detalle diario (client-side: la granularidad día×prop es chica). */
const PAGE_SIZE = 20;

@Component({
  selector: 'app-reputation-dashboard-page',
  imports: [
    DecimalPipe,
    PageHeaderComponent,
    LoadingStateComponent,
    ErrorStateComponent,
    EmptyStateComponent,
    KpiChartComponent,
    PropertySelectorComponent,
    HorizontalSubNavComponent,
  ],
  templateUrl: './reputation-dashboard-page.html',
  styleUrl: './reputation-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReputationDashboardPageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly reviewsApi = inject(ReviewsApiService);
  private readonly reports = inject(ReportsExportService);
  private readonly auth = inject(AuthService);
  private readonly propertyCtx = inject(PropertyContextService);

  /** Descarga del informe gateada por ``reports.download``. */
  readonly canExport = computed(() => this.auth.hasPermission(REPORTS_DOWNLOAD));

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });
  readonly selectedPropId = computed(() => {
    const fromQuery = Number(this.qp()?.get('prop_id') ?? '0');
    if (fromQuery) return fromQuery;
    return this.propertyCtx.currentPropId() || 0;
  });
  readonly selectedLabel = signal(this.activatedRoute.snapshot.queryParamMap.get('prop_label') ?? '');
  readonly days = computed(() => Number(this.qp()?.get('days') ?? '30'));
  readonly hasPropId = computed(() => this.selectedPropId() > 0);

  readonly DAYS_OPTIONS = [7, 30, 90, 365] as const;
  readonly PAGE_SIZE = PAGE_SIZE;

  // ── Compuesto (TA12 M1.2/M1.3/M1.4): ClickHouse kpi_review_daily ──
  // No dispara la petición sin prop_id: evita el 400 "Contexto de hotel requerido"
  // que ve super_admin al entrar a /management/reviews/dashboard sin ?prop_id.
  private readonly analyticsResource = rxResource<ReviewAnalytics | null, { propId: number; days: number } | undefined>({
    params: () => {
      const pid = this.selectedPropId();
      const days = this.days();
      return pid ? { propId: pid, days } : undefined;
    },
    stream: ({ params }) => {
      if (!params) return of(null as unknown as ReviewAnalytics);
      return this.reviewsApi.getReputationAnalytics(params.propId, params.days);
    },
  });

  readonly analyticsLoading = computed(() => this.hasPropId() ? this.analyticsResource.isLoading() : false);
  readonly analyticsError = computed(() => this.hasPropId() ? this.analyticsResource.error() : null);
  private readonly analyticsValue = this.analyticsResource.value;
  readonly analyticsAvailable = computed(() => Boolean(this.analyticsValue()?.available));
  readonly analyticsMessage = computed(() => this.analyticsValue()?.message ?? '');
  readonly rows = computed<ReviewAnalyticsRow[]>(() => this.analyticsValue()?.rows ?? []);

  // ── Simple (M1.x Mongo): recientes/departamental para aside y export ──
  readonly mongoData = signal<ReputationDashboard | null>(null);
  readonly mongoLoading = signal(false);

  constructor() {
    const reloadMongo = (): void => {
      const propId = this.selectedPropId();
      const days = this.days();
      if (!propId) {
        this.mongoData.set(null);
        this.mongoLoading.set(false);
        return;
      }
      this.mongoLoading.set(true);
      this.reviewsApi
        .getReputationDashboard(propId, days)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (res) => { this.mongoData.set(res); this.mongoLoading.set(false); },
          error: () => { this.mongoData.set(null); this.mongoLoading.set(false); },
        });
    };
    // Carga inicial diferida: espera a que PropertyContext esté listo para no pedir sin prop_id.
    effect(() => {
      // Dependencias reactivas: propId (query o contexto) + days + ready
      void this.propertyCtx.ready();
      const pid = this.selectedPropId();
      void this.days();
      if (!pid) {
        this.mongoData.set(null);
        return;
      }
      reloadMongo();
    });
  }

  // ── Totales del compuesto (Σ sobre kpi_review_daily) ──
  readonly totals = computed(() => {
    let reviews = 0, approved = 0, ratingSum = 0, responded = 0;
    let respondedCount = 0, responseSum = 0;
    let positive = 0, neutral = 0, negative = 0;
    for (const row of this.rows()) {
      reviews += row.reviews;
      approved += row.approved;
      ratingSum += row.avgRating * row.approved;
      responded += row.responded;
      respondedCount += row.respondedCount;
      responseSum += (row.avgResponseMinutes ?? 0) * row.respondedCount;
      positive += row.positive;
      neutral += row.neutral;
      negative += row.negative;
    }
    const avgRating = approved ? ratingSum / approved : 0;
    return {
      reviews,
      avgRating,
      gri: Math.round((avgRating / 5) * 100),
      responded,
      responseRatePct: reviews ? Math.round((responded / reviews) * 100) : 0,
      avgResponseMinutes: respondedCount ? responseSum / respondedCount : null,
      avgResponseHours: respondedCount ? responseSum / respondedCount / 60 : null,
      sentiment: { positive, neutral, negative },
      sentimentTotal: positive + neutral + negative,
    };
  });

  // ── Grilla diaria paginada (client-side) ──
  readonly page = signal(1);
  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.rows().length / PAGE_SIZE)));
  readonly pagedRows = computed(() => {
    const start = (this.page() - 1) * PAGE_SIZE;
    return this.rows().slice(start, start + PAGE_SIZE);
  });

  goToPage(page: number): void {
    this.page.set(Math.min(Math.max(1, page), this.totalPages()));
  }

  setDays(days: number): void {
    this.page.set(1);
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { days },
      queryParamsHandling: 'merge',
    });
  }

  onPropertySelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    this.page.set(1);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, label);
    } else {
      this.propertyCtx.clear();
    }
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: event.propId || null, prop_label: label || null },
      queryParamsHandling: 'merge',
    });
  }

  // ── Chart inputs ──
  readonly chartLabels = computed(() => this.rows().map((r) => r.date));
  readonly chartDatasets = computed<KpiChartDataset[]>(() => [
    { label: 'Rating medio', data: this.rows().map((r) => Number(r.avgRating.toFixed(2))) },
  ]);

  // ── Exportaciones (informe simple Mongo + totales compuestos) ──
  readonly exporting = signal(false);

  exportPDF(): void {
    this.exporting.set(true);
    void this.runPdfExport().finally(() => this.exporting.set(false));
  }

  exportXlsx(): void {
    this.exporting.set(true);
    void this.runXlsxExport().finally(() => this.exporting.set(false));
  }

  private async runPdfExport(): Promise<void> {
    const d = this.mongoData();
    const t = this.totals();
    if (!d) return;

    const grid = buildSummaryGrid([
      {
        label: 'Global Review Index',
        value: `${t.gri} / 100`,
        tone: t.gri >= 80 ? 'positive' : t.gri >= 60 ? 'warning' : 'negative',
      },
      { label: 'Cambio vs. período anterior', value: `${d.griChange > 0 ? '+' : ''}${d.griChange} pts`, tone: d.griChange >= 0 ? 'positive' : 'negative' },
      { label: 'Total de reseñas', value: String(d.totalReviews), tone: 'neutral' },
      { label: 'Meta GRI', value: String(d.griTarget), tone: 'neutral' },
    ]);

    const deptTable = d.departmental.length
      ? buildTable(
          [
            { label: 'Departamento' },
            { label: 'Puntuación', align: 'right' },
            { label: 'Positivo', align: 'right' },
            { label: 'Neutral', align: 'right' },
            { label: 'Negativo', align: 'right' },
            { label: 'Valoraciones', align: 'right' },
          ],
          d.departmental.map((dept) => [
            dept.label,
            `${dept.score}%`,
            `${dept.positivePct}%`,
            `${dept.neutralPct}%`,
            `${dept.negativePct}%`,
            String(dept.totalRatings),
          ]),
        )
      : `<p style="color: var(--c-text-muted); font-style: italic;">Sin valoraciones departamentales en este período.</p>`;

    const feedbackTable = d.recentFeedback.length
      ? buildTable(
          [
            { label: 'Huésped' },
            { label: 'Rating', align: 'center' },
            { label: 'Comentario' },
            { label: 'Fecha', align: 'right' },
          ],
          d.recentFeedback.map((f) => [
            f.userName,
            '★'.repeat(f.rating) + '☆'.repeat(5 - f.rating),
            f.comment || 'Sin comentario',
            new Date(f.createdAt).toLocaleDateString('es-MX'),
          ]),
        )
      : `<p style="color: var(--c-text-muted); font-style: italic;">No hay reseñas recientes.</p>`;

    const dailyTable = this.rows().length
      ? buildTable(
          [
            { label: 'Fecha' },
            { label: 'Reseñas', align: 'right' },
            { label: 'Aprobadas', align: 'right' },
            { label: 'Respondidas', align: 'right' },
            { label: 'Rating medio', align: 'right' },
          ],
          this.rows().map((row) => [
            row.date,
            String(row.reviews),
            String(row.approved),
            String(row.responded),
            row.avgRating.toFixed(2),
          ]),
        )
      : '';

    const bodyHtml = `
      ${grid}
      <h2>Valoraciones departamentales</h2>
      ${deptTable}
      <h2 class="page-break">Reseñas recientes</h2>
      ${feedbackTable}
      ${dailyTable ? `<h2>Detalle diario (kpi_review_daily)</h2>${dailyTable}` : ''}
    `;

    const html = buildReportShell({
      title: 'Reporte de Reputación',
      subtitle: `Últimos ${this.days()} días`,
      generatedAt: new Date(),
      metaRows: [
        { label: 'Período', value: `Últimos ${this.days()} días` },
        { label: 'GRI', value: `${t.gri} / 100` },
        { label: 'Total reseñas', value: String(t.reviews) },
      ],
      bodyHtml,
    });

    await this.reports.exportPdf(html, `HotelData-Reporte-Reputacion-${new Date().toISOString().slice(0, 10)}`, 'Reporte de Reputación');
  }

  private async runXlsxExport(): Promise<void> {
    const d = this.mongoData();
    const t = this.totals();
    if (!d) return;

    await this.reports.exportXlsx({
      filename: `HotelData-Reporte-Reputacion-${new Date().toISOString().slice(0, 10)}`,
      sheet_title: `Reputación · Últimos ${this.days()} días`,
      sheets: [
        {
          name: 'Resumen',
          headers: [{ label: 'Métrica' }, { label: 'Valor', align: 'right' }],
          rows: [
            ['GRI', t.gri],
            ['Cambio vs período anterior', d.griChange],
            ['Meta GRI', d.griTarget],
            ['Total reseñas', t.reviews],
            ['Tasa de respuesta (%)', t.responseRatePct],
            ['Respuesta media (min)', t.avgResponseMinutes === null ? '—' : Math.round(t.avgResponseMinutes)],
            ['Período (días)', this.days()],
          ],
          column_widths: { A: 30, B: 16 },
        },
        {
          name: 'Departamental',
          headers: [
            { label: 'Departamento' },
            { label: 'Puntuación' },
            { label: 'Positivo %' },
            { label: 'Neutral %' },
            { label: 'Negativo %' },
            { label: 'Valoraciones' },
          ],
          rows: d.departmental.map((dept) => [
            dept.label, dept.score, dept.positivePct, dept.neutralPct, dept.negativePct, dept.totalRatings,
          ]),
          column_widths: { A: 24, B: 14, C: 14, D: 14, E: 14, F: 16 },
        },
        {
          name: 'Reseñas recientes',
          headers: [
            { label: 'Fecha' },
            { label: 'Huésped' },
            { label: 'Rating' },
            { label: 'Comentario' },
          ],
          rows: d.recentFeedback.map((f) => [
            new Date(f.createdAt).toLocaleString('es-MX'),
            f.userName,
            f.rating,
            f.comment || 'Sin comentario',
          ]),
          column_widths: { A: 22, B: 24, C: 10, D: 60 },
        },
        {
          name: 'Detalle diario',
          headers: [
            { label: 'Fecha' },
            { label: 'Reseñas', align: 'right' },
            { label: 'Aprobadas', align: 'right' },
            { label: 'Pendientes', align: 'right' },
            { label: 'Rechazadas', align: 'right' },
            { label: 'Respondidas', align: 'right' },
            { label: 'Rating medio', align: 'right' },
          ],
          rows: this.rows().map((row) => [
            row.date, row.reviews, row.approved, row.pending, row.rejected, row.responded, row.avgRating,
          ]),
          column_widths: { A: 14, B: 12, C: 12, D: 12, E: 12, F: 13, G: 13 },
        },
      ],
    });
  }
}
