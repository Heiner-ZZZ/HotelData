import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ReportsExportService } from '../../../../shared/services/reports-export.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import {
  buildReportShell,
  buildSummaryGrid,
  buildTable,
} from '../../../../shared/utils/report-html-templates';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReputationDashboard, ReviewAnalytics } from '../../models/reviews.model';
import { ReviewsApiService } from '../../services/reviews-api.service';

@Component({
  selector: 'app-reputation-dashboard-page',
  standalone: true,
  imports: [FormsModule, DecimalPipe, PageHeaderComponent, LoadingStateComponent, ErrorStateComponent, EmptyStateComponent, PropertySelectorComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="reputation-page" style="max-width: 1200px; margin: 0 auto; padding: 24px;">
      <app-page-header
        eyebrow="Reputation Intelligence"
        title="Panel de Reputación"
        description="Índice de satisfacción global y análisis departamental."
      >
        <app-property-selector slot="actions" [selectedPropId]="selectedPropId()" [selectedLabel]="selectedLabel()" (propIdChange)="onPropertySelected($event)" />
      </app-page-header>

      <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 24px; flex-wrap: wrap;">
        <select [ngModel]="selectedDays()" (ngModelChange)="selectedDays.set($event); loadDashboard()"
          style="background: var(--surface); border: 1px solid var(--app-border); border-radius: 8px; padding: 8px 12px; font-size: 13px; color: var(--app-text);">
          <option [value]="30">Últimos 30 días</option>
          <option [value]="60">Últimos 60 días</option>
          <option [value]="90">Últimos 90 días</option>
          <option [value]="365">Último año</option>
        </select>
        <button (click)="exportPDF()" [disabled]="exporting()"
          style="display: flex; align-items: center; gap: 6px; background: var(--surface); border: 1px solid var(--app-border); border-radius: 8px; padding: 8px 16px; font-size: 13px; color: var(--app-text); cursor: pointer;">
          <span class="material-symbols-outlined" style="font-size: 16px;">picture_as_pdf</span>
          {{ exporting() ? 'Exportando...' : 'Exportar PDF' }}
        </button>
        <button (click)="exportXlsx()" [disabled]="exporting()"
          style="display: flex; align-items: center; gap: 6px; background: var(--surface); border: 1px solid var(--app-border); border-radius: 8px; padding: 8px 16px; font-size: 13px; color: var(--app-text); cursor: pointer;">
          <span class="material-symbols-outlined" style="font-size: 16px;">table_chart</span>
          {{ exporting() ? 'Exportando...' : 'Exportar Excel' }}
        </button>
      </div>

      @if (analytics(); as a) {
        <section style="margin-bottom: 24px; background: var(--surface); border: 1px solid var(--app-border); border-radius: 12px; padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;">
            <div>
              <h2 style="margin: 0; font-size: 16px;">Capa analítica horaria</h2>
              <p style="margin: 4px 0 0; color: var(--muted-text); font-size: 12px;">KPI agregado desde MongoDB hacia ClickHouse · {{ a.days }} días</p>
            </div>
            <span style="font-size: 12px; color: var(--muted-text);">{{ a.available ? 'Disponible' : 'Aún no disponible' }}</span>
          </div>
          @if (a.available && a.rows.length) {
            <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;">
              <div class="surface-card" style="padding: 14px;"><small>Reseñas</small><strong style="display: block; font-size: 22px;">{{ analyticsTotals().reviews }}</strong></div>
              <div class="surface-card" style="padding: 14px;"><small>Rating medio</small><strong style="display: block; font-size: 22px;">{{ analyticsTotals().avgRating | number:'1.1-2' }}/5</strong></div>
              <div class="surface-card" style="padding: 14px;"><small>Respondidas</small><strong style="display: block; font-size: 22px;">{{ analyticsTotals().responded }}</strong></div>
              <div class="surface-card" style="padding: 14px;"><small>Moderación media</small><strong style="display: block; font-size: 22px;">{{ analyticsTotals().moderationMinutes === null ? '—' : (analyticsTotals().moderationMinutes | number:'1.0-1') + ' min' }}</strong></div>
            </div>
          } @else {
            <p style="margin: 0; color: var(--muted-text); font-size: 13px;">{{ a.message || 'El DAG horario todavía no ha cargado kpi_review_daily.' }}</p>
          }
        </section>
      }

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando dashboard..." /> }
        @case ('error') { <app-error-state title="Error" description="No se pudo cargar el dashboard de reputación." /> }
        @case ('empty') { <app-empty-state icon="reviews" title="Sin datos" description="No hay reseñas aprobadas en el período seleccionado." /> }
        @default {
          @if (data(); as d) {
            <!-- Top row: GRI + Departmental -->
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 20px; margin-bottom: 24px;">

              <!-- GRI Card -->
              <div style="background: var(--surface); border: 1px solid var(--app-border); border-radius: 12px; padding: 24px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                  <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted-text); margin-bottom: 16px;">Global Review Index</div>
                  <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px;">
                    <span style="font-size: 36px; font-weight: 700; color: var(--app-text);">{{ d.gri }}</span>
                    <span style="color: var(--muted-text); font-size: 14px;">/ 100</span>
                  </div>
                  <div style="display: flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 500; color: var(--success); background: var(--success-light); width: fit-content; padding: 2px 8px; border-radius: 4px;">
                    <span class="material-symbols-outlined" style="font-size: 14px;">arrow_upward</span>
                    {{ d.griChange > 0 ? '+' : '' }}{{ d.griChange }} pts
                  </div>
                </div>
                <div style="margin-top: 24px;">
                  <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--muted-text); margin-bottom: 8px;">
                    <span>Meta: {{ d.griTarget }}</span>
                    <span>{{ d.totalReviews }} reseñas</span>
                  </div>
                  <div style="width: 100%; background: var(--surface-hover); border-radius: 999px; height: 6px; overflow: hidden;">
                    <div style="background: var(--accent); height: 6px; border-radius: 999px; transition: width 0.5s;" [style.width.%]="Math.min(100, (d.gri / d.griTarget) * 100)"></div>
                  </div>
                </div>
              </div>

              <!-- Departmental Sentiment -->
              <div style="background: var(--surface); border: 1px solid var(--app-border); border-radius: 12px; padding: 24px;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted-text); margin-bottom: 20px;">Sentimiento Departamental</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
                  @for (dept of d.departmental; track dept.key) {
                    <div>
                      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span class="material-symbols-outlined" style="color: var(--muted-text);">{{ dept.icon }}</span>
                        <span style="font-weight: 600; font-size: 15px;">{{ dept.label }}</span>
                      </div>
                      <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 28px; font-weight: 700;">{{ dept.score }}%</span>
                        <span [style.color]="dept.score >= 80 ? 'var(--success)' : dept.score >= 60 ? 'var(--warning)' : 'var(--danger)'"
                          style="font-size: 12px; font-weight: 500;">
                          {{ dept.score >= 90 ? 'Excelente' : dept.score >= 80 ? 'Positivo' : dept.score >= 60 ? 'Regular' : 'Necesita atención' }}
                        </span>
                      </div>
                      <div style="display: flex; height: 6px; border-radius: 999px; overflow: hidden; background: var(--surface-hover);">
                        <div [style.width.%]="dept.positivePct" style="background: var(--success); transition: width 0.5s;"></div>
                        <div [style.width.%]="dept.neutralPct" style="background: var(--warning); transition: width 0.5s;"></div>
                        <div [style.width.%]="dept.negativePct" style="background: var(--danger); transition: width 0.5s;"></div>
                      </div>
                      <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--muted-text); margin-top: 4px;">
                        <span>{{ dept.totalRatings }} valoraciones</span>
                      </div>
                    </div>
                  }
                  @if (d.departmental.length === 0) {
                    <div style="grid-column: 1 / -1; text-align: center; color: var(--muted-text); padding: 24px;">
                      No hay valoraciones departamentales todavía.
                    </div>
                  }
                </div>
              </div>
            </div>

            <!-- Bottom row: Feedback + Trend -->
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">

              <!-- Recent Feedback -->
              <div style="background: var(--surface); border: 1px solid var(--app-border); border-radius: 12px; overflow: hidden;">
                <div style="padding: 16px; border-bottom: 1px solid var(--app-border); display: flex; justify-content: space-between; align-items: center; background: var(--surface-raised);">
                  <span style="font-weight: 600; font-size: 15px;">Reseñas Recientes</span>
                </div>
                <div style="max-height: 400px; overflow-y: auto;">
                  @for (item of d.recentFeedback; track item.id) {
                    <div style="padding: 16px; border-bottom: 1px solid var(--app-border);">
                      <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                          <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--indigo-light); display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px; color: var(--indigo-strong);">
                            {{ item.userName.charAt(0).toUpperCase() }}
                          </div>
                          <div>
                            <div style="font-weight: 500; font-size: 14px;">{{ item.userName }}</div>
                          </div>
                        </div>
                        <div style="display: flex; gap: 2px;">
                          @for (star of [1,2,3,4,5]; track star) {
                            <span class="material-symbols-outlined" style="font-size: 14px; color: var(--yellow);">
                              {{ star <= item.rating ? 'star' : 'star_border' }}
                            </span>
                          }
                        </div>
                      </div>
                      <p style="margin: 0; font-size: 13px; color: var(--app-text); line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                        {{ item.comment || 'Sin comentario' }}
                      </p>
                    </div>
                  }
                  @if (d.recentFeedback.length === 0) {
                    <div style="text-align: center; padding: 40px; color: var(--muted-text);">No hay reseñas recientes.</div>
                  }
                </div>
              </div>

              <!-- Trend Chart (simplified bar chart) -->
              <div style="background: var(--surface); border: 1px solid var(--app-border); border-radius: 12px; padding: 24px; display: flex; flex-direction: column;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted-text); margin-bottom: 16px;">Tendencia de Reseñas</div>
                @if (d.dailyCounts.length > 0) {
                  <div style="flex: 1; display: flex; align-items: end; gap: 4px; padding-top: 16px;">
                    @for (day of d.dailyCounts.slice(-14); track day.date) {
                      <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                        <div style="width: 100%; background: var(--accent); border-radius: 4px 4px 0 0; transition: height 0.3s; min-height: 4px;"
                          [style.height]="Math.max(4, (day.count / maxCount()) * 120) + 'px'">
                        </div>
                        <span style="font-size: 9px; color: var(--muted-text); transform: rotate(-45deg); white-space: nowrap;">{{ day.date.slice(5) }}</span>
                      </div>
                    }
                  </div>
                } @else {
                  <div style="flex: 1; display: flex; align-items: center; justify-content: center; color: var(--muted-text); font-size: 13px;">
                    Sin datos de tendencia.
                  </div>
                }
              </div>
            </div>
          }
        }
      }
    </div>
  `
})
export class ReputationDashboardPageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly reviewsApi = inject(ReviewsApiService);
  private readonly reports = inject(ReportsExportService);
  readonly propertyCtx = inject(PropertyContextService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReputationDashboard | null>(null);
  readonly analytics = signal<ReviewAnalytics | null>(null);
  readonly selectedDays = signal(30);
  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');
  readonly exporting = signal(false);

  readonly Math = Math;

  readonly analyticsTotals = computed(() => {
    const rows = this.analytics()?.rows ?? [];
    const reviews = rows.reduce((sum, row) => sum + row.reviews, 0);
    const approved = rows.reduce((sum, row) => sum + row.approved, 0);
    const ratingSum = rows.reduce((sum, row) => sum + row.avgRating * row.approved, 0);
    const responded = rows.reduce((sum, row) => sum + row.responded, 0);
    const moderated = rows.reduce((sum, row) => sum + row.moderatedCount, 0);
    const moderationTotal = rows.reduce((sum, row) => sum + (row.avgModerationMinutes ?? 0) * row.moderatedCount, 0);
    return {
      reviews,
      avgRating: approved ? ratingSum / approved : 0,
      responded,
      moderationMinutes: moderated ? moderationTotal / moderated : null,
    };
  });

  readonly maxCount = computed(() => {
    const counts = this.data()?.dailyCounts ?? [];
    return Math.max(1, ...counts.map(c => c.count));
  });

  constructor() {
    const propId = Number(new URLSearchParams(window.location.search).get('prop_id') ?? '0');
    this.selectedPropId.set(propId);
    this.selectedLabel.set(propId ? this.propertyCtx.assignedProperties().find(p => p.propId === propId)?.label ?? '' : '');
    this.loadDashboard();
  }

  onPropertySelected(event: { propId: number; label: string }) {
    this.selectedPropId.set(event.propId || 0);
    this.selectedLabel.set(event.label);
    const query = event.propId ? `?prop_id=${event.propId}` : '';
    window.history.replaceState({}, '', `${window.location.pathname}${query}`);
    this.loadDashboard();
  }

  loadDashboard() {
    this.viewState.set('loading');
    this.reviewsApi.getReputationAnalytics(this.selectedPropId() || undefined, this.selectedDays()).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: result => this.analytics.set(result),
      error: () => this.analytics.set({ available: false, days: this.selectedDays(), rows: [], message: 'No se pudo consultar la capa analítica.' }),
    });
    this.reviewsApi.getReputationDashboard(this.selectedPropId() || undefined, this.selectedDays()).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (result) => {
        this.data.set(result);
        this.viewState.set(result.totalReviews > 0 ? 'success' : 'empty');
      },
      error: () => this.viewState.set('error'),
    });
  }

  exportPDF() {
    this.exporting.set(true);
    void this.runPdfExport().finally(() => this.exporting.set(false));
  }

  exportXlsx() {
    this.exporting.set(true);
    void this.runXlsxExport().finally(() => this.exporting.set(false));
  }

  private async runPdfExport(): Promise<void> {
    const d = this.data();
    if (!d) return;

    const grid = buildSummaryGrid([
      {
        label: 'Global Review Index',
        value: `${d.gri} / 100`,
        tone: d.gri >= 80 ? 'positive' : d.gri >= 60 ? 'warning' : 'negative',
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

    const trendTable = d.dailyCounts.length
      ? buildTable(
          [
            { label: 'Fecha' },
            { label: 'Reseñas', align: 'right' },
          ],
          d.dailyCounts.slice(-30).map((c) => [c.date, String(c.count)]),
          [`Total últimos ${Math.min(30, d.dailyCounts.length)} días`, String(d.dailyCounts.slice(-30).reduce((s, c) => s + c.count, 0))],
        )
      : '';

    const bodyHtml = `
      ${grid}
      <h2>Valoraciones departamentales</h2>
      ${deptTable}
      <h2 class="page-break">Reseñas recientes</h2>
      ${feedbackTable}
      ${trendTable ? `<h2>Tendencia diaria</h2>${trendTable}` : ''}
    `;

    const html = buildReportShell({
      title: 'Reporte de Reputación',
      subtitle: `Últimos ${this.selectedDays()} días`,
      generatedAt: new Date(),
      metaRows: [
        { label: 'Período', value: `Últimos ${this.selectedDays()} días` },
        { label: 'GRI', value: `${d.gri} / 100` },
        { label: 'Total reseñas', value: String(d.totalReviews) },
      ],
      bodyHtml,
    });

    await this.reports.exportPdf(html, `HotelData-Reporte-Reputacion-${new Date().toISOString().slice(0, 10)}`, 'Reporte de Reputación');
  }

  private async runXlsxExport(): Promise<void> {
    const d = this.data();
    if (!d) return;
    await this.reports.exportXlsx({
      filename: `HotelData-Reporte-Reputacion-${new Date().toISOString().slice(0, 10)}`,
      sheet_title: `Reputación · Últimos ${this.selectedDays()} días`,
      sheets: [
        {
          name: 'Resumen',
          headers: [{ label: 'Métrica' }, { label: 'Valor', align: 'right' }],
          rows: [
            ['GRI', d.gri],
            ['Cambio vs período anterior', d.griChange],
            ['Meta GRI', d.griTarget],
            ['Total reseñas', d.totalReviews],
            ['Período (días)', this.selectedDays()],
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
          name: 'Tendencia',
          headers: [{ label: 'Fecha' }, { label: 'Reseñas', align: 'right' }],
          rows: d.dailyCounts.map((c) => [c.date, c.count]),
          column_widths: { A: 16, B: 14 },
        },
      ],
    });
  }
}
