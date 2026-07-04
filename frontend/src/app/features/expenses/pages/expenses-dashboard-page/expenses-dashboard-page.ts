import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { BaseChartDirective } from 'ng2-charts';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ExpensesApiService } from '../../services/expenses-api.service';
import type { ExpenseDashboard } from '../../models/expenses.model';

Chart.register(...registerables);

@Component({
  selector: 'app-expenses-dashboard-page',
  standalone: true,
  imports: [CurrencyPipe, RouterLink, PageHeaderComponent, LoadingStateComponent, BaseChartDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="max-width: 1200px; margin: 0 auto; padding: 24px;">
      <app-page-header
        eyebrow="Financeiro"
        title="Control de Gastos y Compras"
        description="Visión general del estado financiero operativo."
      />

      <div style="display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap;">
        <a [routerLink]="['/management/expenses/invoices']"
          style="padding: 8px 16px; border: 1px solid #e2e8f0; border-radius: 8px; background: white; font-size: 13px; text-decoration: none; color: #475569;">
          Ver Facturas
        </a>
        <a [routerLink]="['/management/expenses/invoices/new']"
          style="display: flex; align-items: center; gap: 6px; padding: 8px 16px; background: #2563eb; color: white; border-radius: 8px; font-size: 13px; font-weight: 500; text-decoration: none;">
          <span class="material-symbols-outlined" style="font-size: 16px;">add</span> Nueva Factura
        </a>
        <a [routerLink]="['/management/expenses/ledger']"
          style="display: flex; align-items: center; gap: 6px; padding: 8px 16px; background: #006076; color: white; border-radius: 8px; font-size: 13px; font-weight: 500; text-decoration: none;">
          <span class="material-symbols-outlined" style="font-size: 16px;">account_balance</span> Libro Mayor
        </a>
      </div>

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando dashboard..." /> }
        @case ('error') { <div style="text-align: center; padding: 40px; color: #dc2626;">Error al cargar el dashboard.</div> }
        @default {
          @if (data(); as d) {
            <!-- KPI Cards -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px;">
              <!-- KPI 1: Total expenses -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; position: relative; overflow: hidden;">
                <div style="position: absolute; right: -20px; top: -20px; width: 100px; height: 100px; background: rgba(239,68,68,0.08); border-radius: 50%;"></div>
                <div style="display: flex; justify-content: space-between; align-items: start;">
                  <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b;">Gastos Totales (Mes)</span>
                  <span class="material-symbols-outlined" style="color: #ef4444; font-size: 20px;">trending_up</span>
                </div>
                <div style="font-size: 28px; font-weight: 700; color: #0f172a; margin-top: 8px;">{{ d.monthTotal | currency:'MXN':'symbol-narrow':'1.0-0' }}</div>
              </div>

              <!-- KPI 2: Budget execution -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; position: relative; overflow: hidden;">
                <div style="position: absolute; right: -20px; top: -20px; width: 100px; height: 100px; background: rgba(37,99,235,0.08); border-radius: 50%;"></div>
                <div style="display: flex; justify-content: space-between; align-items: start;">
                  <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b;">Presupuesto Ejecutado</span>
                  <span class="material-symbols-outlined" style="color: #2563eb; font-size: 20px;">account_balance_wallet</span>
                </div>
                <div style="font-size: 28px; font-weight: 700; color: #0f172a; margin-top: 8px;">{{ d.budgetExecutionPct }}%</div>
                <div style="width: 100%; background: #f1f5f9; border-radius: 999px; height: 6px; margin-top: 8px; overflow: hidden;">
                  <div style="background: #2563eb; height: 6px; border-radius: 999px; transition: width 0.5s;" [style.width.%]="d.budgetExecutionPct"></div>
                </div>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Quedan {{ d.budgetRemaining | currency:'MXN':'symbol-narrow':'1.0-0' }}</div>
              </div>

              <!-- KPI 3: Pending approval -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; position: relative; overflow: hidden;">
                <div style="position: absolute; right: -20px; top: -20px; width: 100px; height: 100px; background: rgba(234,179,8,0.08); border-radius: 50%;"></div>
                <div style="display: flex; justify-content: space-between; align-items: start;">
                  <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b;">Pendiente de Aprobación</span>
                  <span class="material-symbols-outlined" style="color: #eab308; font-size: 20px;">pending_actions</span>
                </div>
                <div style="font-size: 28px; font-weight: 700; color: #0f172a; margin-top: 8px;">{{ d.pendingCount }}</div>
                <div style="font-size: 12px; color: #eab308; font-weight: 500; margin-top: 4px;">Valor: {{ d.pendingValue | currency:'MXN':'symbol-narrow':'1.0-0' }}</div>
              </div>
            </div>

            <!-- Bar Chart: Monthly Evolution -->
            @if (d.monthlyBreakdown.length > 1) {
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                  <h3 style="font-size: 15px; font-weight: 600; color: #0f172a; margin: 0;">Evolución de Gastos Mensuales</h3>
                  <span style="font-size: 11px; color: #94a3b8;">Últimos {{ d.monthlyBreakdown.length }} meses</span>
                </div>
                <div style="height: 260px; position: relative;">
                  <canvas
                    baseChart
                    [data]="barChartData()"
                    [options]="barChartOptions"
                    [type]="'bar'"
                    style="width: 100%; height: 100%;"
                  ></canvas>
                </div>
              </div>
            }

            <!-- Bottom: Categories breakdown -->
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
              <h3 style="font-size: 15px; font-weight: 600; color: #0f172a; margin: 0 0 16px;">Gastos por Categoría</h3>
              @if (d.byCategory.length > 0) {
                <div style="display: flex; flex-direction: column; gap: 12px;">
                  @for (cat of d.byCategory; track cat.category) {
                    <div style="display: flex; align-items: center; gap: 12px;">
                      <span style="min-width: 120px; font-size: 13px; font-weight: 500; color: #334155;">{{ cat.category }}</span>
                      <div style="flex: 1; height: 8px; background: #f1f5f9; border-radius: 999px; overflow: hidden;">
                        <div style="height: 8px; border-radius: 999px; background: linear-gradient(90deg, #2563eb, #7c3aed); transition: width 0.5s;"
                          [style.width.%]="d.totalBudget > 0 ? (cat.total / d.totalBudget * 100) : 0"></div>
                      </div>
                      <span style="min-width: 80px; text-align: right; font-size: 13px; font-weight: 600; color: #0f172a;">{{ cat.total | currency:'MXN':'symbol-narrow':'1.0-0' }}</span>
                      <span style="min-width: 40px; text-align: right; font-size: 11px; color: #94a3b8;">{{ cat.count }} fact.</span>
                    </div>
                  }
                </div>
              } @else {
                <p style="font-size: 13px; color: #94a3b8; text-align: center; padding: 24px;">No hay datos de gastos por categoría.</p>
              }
            </div>
          }
        }
      }
    </div>
  `,
})
export class ExpensesDashboardPageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly expensesApi = inject(ExpensesApiService);

  readonly viewState = signal<'loading' | 'success' | 'error'>('loading');
  readonly data = signal<ExpenseDashboard | null>(null);
  readonly barChartData = signal<{ labels: string[]; datasets: { label: string; data: number[]; backgroundColor: string | string[]; borderColor: string; borderWidth: number; borderRadius: number; }[] }>({ labels: [], datasets: [] });

  readonly barChartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#1e293b',
        titleFont: { family: 'Inter', size: 12 },
        bodyFont: { family: 'Inter', size: 13 },
        padding: 12,
        cornerRadius: 8,
        callbacks: {
          label: (ctx: any) => `MXN ${ctx.parsed.y.toLocaleString('es-MX')}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          font: { family: 'Inter', size: 11 },
          color: '#94a3b8',
          maxRotation: 0,
        },
      },
      y: {
        grid: { color: '#f1f5f9', drawBorder: false },
        ticks: {
          font: { family: 'Inter', size: 11 },
          color: '#94a3b8',
          callback: (val: any) => `${(val / 1000).toFixed(0)}k`,
        },
        beginAtZero: true,
      },
    },
  };

  constructor() {
    this.expensesApi.getDashboard().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.data.set(result);
        this.viewState.set('success');
        this.buildChartData(result);
      },
      error: () => this.viewState.set('error'),
    });
  }

  private buildChartData(d: ExpenseDashboard): void {
    if (!d.monthlyBreakdown || d.monthlyBreakdown.length === 0) return;

    const months: Record<string, string> = {
      '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr',
      '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago',
      '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic',
    };
    const labels = d.monthlyBreakdown.map((m) => {
      const parts = m.month.split('-');
      const monthLabel = months[parts[1]] || parts[1];
      return `${monthLabel} ${parts[0]}`;
    });
    const values = d.monthlyBreakdown.map((m) => m.total);

    const maxVal = Math.max(...values);
    const gradientColors = values.map((v) => {
      const ratio = maxVal > 0 ? v / maxVal : 0.3;
      const opacity = 0.4 + ratio * 0.6;
      return `rgba(37, 99, 235, ${opacity})`;
    });

    this.barChartData.set({
      labels,
      datasets: [
        {
          label: 'Gastos',
          data: values,
          backgroundColor: gradientColors,
          borderColor: '#2563eb',
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    });
  }
}
