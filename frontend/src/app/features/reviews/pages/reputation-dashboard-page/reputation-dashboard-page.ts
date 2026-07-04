import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ReportsExportService } from '../../../../shared/services/reports-export.service';
import {
  buildReportShell,
  buildSummaryGrid,
  buildTable,
  esc,
} from '../../../../shared/utils/report-html-templates';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReputationDashboard } from '../../models/reviews.model';
import { ReviewsApiService } from '../../services/reviews-api.service';

@Component({
  selector: 'app-reputation-dashboard-page',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, FormsModule, PageHeaderComponent, LoadingStateComponent, ErrorStateComponent, EmptyStateComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="reputation-page" style="max-width: 1200px; margin: 0 auto; padding: 24px;">
      <app-page-header
        eyebrow="Reputation Intelligence"
        title="Panel de Reputación"
        description="Índice de satisfacción global y análisis departamental."
      />

      <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 24px; flex-wrap: wrap;">
        <select [ngModel]="selectedDays()" (ngModelChange)="selectedDays.set($event); loadDashboard()"
          style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 12px; font-size: 13px;">
          <option [value]="30">Últimos 30 días</option>
          <option [value]="60">Últimos 60 días</option>
          <option [value]="90">Últimos 90 días</option>
          <option [value]="365">Último año</option>
        </select>
        <button (click)="exportPDF()" [disabled]="exporting()"
          style="display: flex; align-items: center; gap: 6px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer;">
          <span class="material-symbols-outlined" style="font-size: 16px;">download</span>
          {{ exporting() ? 'Exportando...' : 'Exportar Reporte PDF' }}
        </button>
      </div>

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando dashboard..." /> }
        @case ('error') { <app-error-state title="Error" description="No se pudo cargar el dashboard de reputación." /> }
        @case ('empty') { <app-empty-state icon="reviews" title="Sin datos" description="No hay reseñas aprobadas en el período seleccionado." /> }
        @default {
          @if (data(); as d) {
            <!-- Top row: GRI + Departmental -->
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 20px; margin-bottom: 24px;">

              <!-- GRI Card -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                  <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 16px;">Global Review Index</div>
                  <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px;">
                    <span style="font-size: 36px; font-weight: 700; color: #0f172a;">{{ d.gri }}</span>
                    <span style="color: #64748b; font-size: 14px;">/ 100</span>
                  </div>
                  <div style="display: flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 500; color: #16a34a; background: #f0fdf4; width: fit-content; padding: 2px 8px; border-radius: 4px;">
                    <span class="material-symbols-outlined" style="font-size: 14px;">arrow_upward</span>
                    {{ d.griChange > 0 ? '+' : '' }}{{ d.griChange }} pts
                  </div>
                </div>
                <div style="margin-top: 24px;">
                  <div style="display: flex; justify-content: space-between; font-size: 12px; color: #64748b; margin-bottom: 8px;">
                    <span>Meta: {{ d.griTarget }}</span>
                    <span>{{ d.totalReviews }} reseñas</span>
                  </div>
                  <div style="width: 100%; background: #f1f5f9; border-radius: 999px; height: 6px; overflow: hidden;">
                    <div style="background: #2563eb; height: 6px; border-radius: 999px; transition: width 0.5s;" [style.width.%]="Math.min(100, (d.gri / d.griTarget) * 100)"></div>
                  </div>
                </div>
              </div>

              <!-- Departmental Sentiment -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 20px;">Sentimiento Departamental</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
                  @for (dept of d.departmental; track dept.key) {
                    <div>
                      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span class="material-symbols-outlined" style="color: #64748b;">{{ dept.icon }}</span>
                        <span style="font-weight: 600; font-size: 15px;">{{ dept.label }}</span>
                      </div>
                      <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px;">
                        <span style="font-size: 28px; font-weight: 700;">{{ dept.score }}%</span>
                        <span [style.color]="dept.score >= 80 ? '#16a34a' : dept.score >= 60 ? '#d97706' : '#dc2626'"
                          style="font-size: 12px; font-weight: 500;">
                          {{ dept.score >= 90 ? 'Excelente' : dept.score >= 80 ? 'Positivo' : dept.score >= 60 ? 'Regular' : 'Necesita atención' }}
                        </span>
                      </div>
                      <div style="display: flex; height: 6px; border-radius: 999px; overflow: hidden; background: #f1f5f9;">
                        <div [style.width.%]="dept.positivePct" style="background: #22c55e; transition: width 0.5s;"></div>
                        <div [style.width.%]="dept.neutralPct" style="background: #f59e0b; transition: width 0.5s;"></div>
                        <div [style.width.%]="dept.negativePct" style="background: #ef4444; transition: width 0.5s;"></div>
                      </div>
                      <div style="display: flex; justify-content: space-between; font-size: 10px; color: #94a3b8; margin-top: 4px;">
                        <span>{{ dept.totalRatings }} valoraciones</span>
                      </div>
                    </div>
                  }
                  @if (d.departmental.length === 0) {
                    <div style="grid-column: 1 / -1; text-align: center; color: #94a3b8; padding: 24px;">
                      No hay valoraciones departamentales todavía.
                    </div>
                  }
                </div>
              </div>
            </div>

            <!-- Bottom row: Feedback + Trend -->
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">

              <!-- Recent Feedback -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
                <div style="padding: 16px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; background: #fafafa;">
                  <span style="font-weight: 600; font-size: 15px;">Reseñas Recientes</span>
                </div>
                <div style="max-height: 400px; overflow-y: auto;">
                  @for (item of d.recentFeedback; track item.id) {
                    <div style="padding: 16px; border-bottom: 1px solid #f1f5f9;">
                      <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                          <div style="width: 32px; height: 32px; border-radius: 50%; background: #e0e7ff; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px; color: #4338ca;">
                            {{ item.userName.charAt(0).toUpperCase() }}
                          </div>
                          <div>
                            <div style="font-weight: 500; font-size: 14px;">{{ item.userName }}</div>
                          </div>
                        </div>
                        <div style="display: flex; gap: 2px;">
                          @for (star of [1,2,3,4,5]; track star) {
                            <span class="material-symbols-outlined" style="font-size: 14px; color: #f59e0b;">
                              {{ star <= item.rating ? 'star' : 'star_border' }}
                            </span>
                          }
                        </div>
                      </div>
                      <p style="margin: 0; font-size: 13px; color: #334155; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                        {{ item.comment || 'Sin comentario' }}
                      </p>
                    </div>
                  }
                  @if (d.recentFeedback.length === 0) {
                    <div style="text-align: center; padding: 40px; color: #94a3b8;">No hay reseñas recientes.</div>
                  }
                </div>
              </div>

              <!-- Trend Chart (simplified bar chart) -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; display: flex; flex-direction: column;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 16px;">Tendencia de Reseñas</div>
                @if (d.dailyCounts.length > 0) {
                  <div style="flex: 1; display: flex; align-items: end; gap: 4px; padding-top: 16px;">
                    @for (day of d.dailyCounts.slice(-14); track day.date) {
                      <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                        <div style="width: 100%; background: #2563eb; border-radius: 4px 4px 0 0; transition: height 0.3s; min-height: 4px;"
                          [style.height]="Math.max(4, (day.count / maxCount()) * 120) + 'px'">
                        </div>
                        <span style="font-size: 9px; color: #94a3b8; transform: rotate(-45deg); white-space: nowrap;">{{ day.date.slice(5) }}</span>
                      </div>
                    }
                  </div>
                } @else {
                  <div style="flex: 1; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 13px;">
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

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReputationDashboard | null>(null);
  readonly selectedDays = signal(30);
  readonly exporting = signal(false);

  readonly Math = Math;

  readonly maxCount = computed(() => {
    const counts = this.data()?.dailyCounts ?? [];
    return Math.max(1, ...counts.map(c => c.count));
  });

  constructor() {
    this.loadDashboard();
  }

  loadDashboard() {
    this.viewState.set('loading');
    this.reviewsApi.getReputationDashboard(undefined, this.selectedDays()).pipe(
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
          headers: [{ label: 'Métrica' }, { label: 'Valor', align: 'right' } as any],
          rows: [
            ['GRI', d.gri] as any,
            ['Cambio vs período anterior', d.griChange] as any,
            ['Meta GRI', d.griTarget] as any,
            ['Total reseñas', d.totalReviews] as any,
            ['Período (días)', this.selectedDays()] as any,
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
          ]) as any[],
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
          ]) as any[],
          column_widths: { A: 22, B: 24, C: 10, D: 60 },
        },
        {
          name: 'Tendencia',
          headers: [{ label: 'Fecha' }, { label: 'Reseñas', align: 'right' } as any],
          rows: d.dailyCounts.map((c) => [c.date, c.count] as any),
          column_widths: { A: 16, B: 14 },
        },
      ],
    });
  }
}
