import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
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
    // Dynamic import of jspdf for cleaner loading
    import('jspdf').then(({ default: jsPDF }) => {
      import('jspdf-autotable').then(() => {
        const doc = new jsPDF('p', 'mm', 'a4');
        const d = this.data();
        if (!d) { this.exporting.set(false); return; }

        // System logo placeholder
        doc.setFontSize(18);
        doc.setFont('helvetica', 'bold');
        doc.text('HotelData', 14, 22);
        doc.setFontSize(8);
        doc.setTextColor(100);
        doc.text('Sistema de Gestión Hotelera — Reporte de Reputación', 14, 28);
        doc.text(`Generado: ${new Date().toLocaleDateString('es-MX')}`, 14, 33);

        // GRI Section
        doc.setTextColor(0);
        doc.setFontSize(14);
        doc.setFont('helvetica', 'bold');
        doc.text('Global Review Index', 14, 45);
        doc.setFontSize(22);
        doc.text(`${d.gri} / 100`, 14, 55);
        doc.setFontSize(10);
        doc.setTextColor(100);
        doc.text(`Total de reseñas: ${d.totalReviews} | Cambio: ${d.griChange > 0 ? '+' : ''}${d.griChange} pts`, 14, 62);

        // Departmental section
        doc.setTextColor(0);
        doc.setFontSize(14);
        doc.setFont('helvetica', 'bold');
        doc.text('Valoraciones Departamentales', 14, 75);

        let yPos = 83;
        for (const dept of d.departmental) {
          doc.setFontSize(11);
          doc.setFont('helvetica', 'bold');
          doc.text(`${dept.label}: ${dept.score}%`, 14, yPos);
          doc.setFontSize(9);
          doc.setTextColor(100);
          doc.text(`Positivo: ${dept.positivePct}% | Neutral: ${dept.neutralPct}% | Negativo: ${dept.negativePct}%`, 14, yPos + 5);
          doc.text(`${dept.totalRatings} valoraciones`, 14, yPos + 10);
          yPos += 18;
        }

        // Recent feedback table
        if (d.recentFeedback.length > 0) {
          yPos = Math.max(yPos + 5, 95);
          (doc as any).autoTable({
            startY: yPos,
            head: [['Huésped', 'Rating', 'Comentario']],
            body: d.recentFeedback.map(f => [f.userName, `${f.rating}/5`, f.comment || '']),
            theme: 'plain',
            styles: { fontSize: 8, cellPadding: 3 },
            headStyles: { fontStyle: 'bold', fillColor: [240, 240, 240] },
            alternateRowStyles: { fillColor: [248, 248, 248] },
          });
        }

        doc.save(`HotelData-Reporte-Reputacion-${new Date().toISOString().slice(0, 10)}.pdf`);
        this.exporting.set(false);
      });
    }).catch(() => {
      this.exporting.set(false);
    });
  }
}
