import { ChangeDetectionStrategy, Component, computed, input, ViewChild, inject } from '@angular/core';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';
import type { ChartConfiguration, ChartData, ChartType } from 'chart.js';
import { ThemeService } from '../../../core/theme/theme.service';

export type KpiValueFormat = 'none' | 'currency' | 'number';

/**
 * Dataset configurable per serie: admite gráficos mixtos (bar+line) y eje Y
 * secundario (axis 'y1') con formato propio. Todo es opcional y mantiene
 * compatibilidad con los usos previos que solo pasaban {label, data, color}.
 */
export interface KpiChartDataset {
  label: string;
  data: number[];
  color?: string;
  /** Tipo por dataset; si falta, se usa el `type` del componente. */
  type?: 'bar' | 'line';
  /** Eje Y usado por este dataset ('y' izquierdo por defecto, 'y1' derecho). */
  axis?: 'y' | 'y1';
  /** Formato por dataset para tooltips/ticks; si falta, usa `formatValue`. */
  formatValue?: KpiValueFormat;
}

type ChartDatasetLike = ChartConfiguration['data']['datasets'][number] & { _fmt: KpiValueFormat };

@Component({
  selector: 'app-kpi-chart',
  imports: [BaseChartDirective],
  providers: [provideCharts(withDefaultRegisterables())],
  template: `
    <div class="kpi-chart-wrap">
      @if (title() || showExport()) {
        <div class="kpi-chart-header">
          @if (title()) {
            <h3 class="kpi-chart-title">{{ title() }}</h3>
          }
          @if (showExport()) {
            <button
              type="button"
              class="kpi-chart-export"
              (click)="exportImage(exportFilename())"
              title="Descargar gráfico como PNG"
              aria-label="Descargar gráfico como PNG"
            >
              <span class="material-symbols-outlined">download</span>
            </button>
          }
        </div>
      }
      <div class="chart-container" [style.height.px]="height()">
        <canvas
          baseChart
          [data]="chartData()"
          [options]="chartOptions()"
          [type]="chartType()"
        >
        </canvas>
      </div>
    </div>
  `,
  styles: [
    `
    .kpi-chart-wrap {
      background: var(--surface);
      border: 1px solid var(--app-border);
      border-radius: 12px;
      padding: 1rem 1rem 0.5rem;
      transition: background 0.15s ease, border-color 0.15s ease;
    }
    .kpi-chart-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }
    .kpi-chart-title {
      margin: 0;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--app-text);
      transition: color 0.15s ease;
    }
    .kpi-chart-export {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      flex-shrink: 0;
      border: 1px solid var(--app-border);
      border-radius: 8px;
      background: var(--surface);
      color: var(--muted-text);
      cursor: pointer;
      transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;

      .material-symbols-outlined {
        font-size: 1rem;
      }

      &:hover {
        color: var(--accent-strong);
        border-color: var(--accent);
        background: var(--accent-light);
      }
    }
    .chart-container {
      position: relative;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KpiChartComponent {
  @ViewChild(BaseChartDirective) private readonly chartDirective?: BaseChartDirective;
  private readonly themeService = inject(ThemeService);

  readonly title = input<string>('');
  readonly labels = input<string[]>([]);
  readonly datasets = input<KpiChartDataset[]>([]);
  readonly type = input<'bar' | 'line'>('bar');
  readonly height = input(200);
  readonly showLegend = input(false);
  readonly formatValue = input<KpiValueFormat>('none');
  /** Muestra el botón de descarga PNG en el header del gráfico. */
  readonly showExport = input(false);
  /** Nombre base del archivo PNG descargado (sin extensión). */
  readonly exportFilename = input('chart');

  readonly chartType = computed((): ChartType => this.type());
  readonly isDark = this.themeService.isDark;

  readonly colors = ['#1463ff', '#22c55e', '#a78bfa', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];

  readonly chartData = computed((): ChartData => {
    const lbls = this.labels();
    const ds = this.datasets();
    const defaultType = this.type();
    return {
      labels: lbls,
      datasets: ds.map((d, i) => {
        const t = d.type ?? defaultType;
        const isLine = t === 'line';
        const item: ChartDatasetLike = {
          label: d.label,
          data: d.data,
          type: t,
          yAxisID: d.axis ?? 'y',
          // Dibuja la línea por encima de las barras en gráficos mixtos.
          order: isLine ? 2 : 1,
          backgroundColor: d.color || this.colors[i % this.colors.length] + 'cc',
          borderColor: d.color || this.colors[i % this.colors.length],
          borderWidth: 2,
          fill: isLine ? false : undefined,
          tension: isLine ? 0.3 : undefined,
          pointRadius: isLine ? 3 : 0,
          pointHoverRadius: 5,
          barPercentage: 0.6,
          categoryPercentage: 0.8,
          _fmt: d.formatValue ?? this.formatValue(),
        };
        return item;
      }),
    };
  });

  readonly chartOptions = computed((): ChartConfiguration['options'] => {
    const fmt = this.formatValue();
    const isDark = this.isDark();
    const ds = this.datasets();
    const hasY1 = ds.some((d) => d.axis === 'y1');
    const y1Fmt = ds.find((d) => d.axis === 'y1')?.formatValue ?? fmt;
    const tickColor = isDark ? '#8b949e' : '#5f6f87';
    const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
    const tickFmt = (value: string | number, useFmt: KpiValueFormat): string => {
      if (useFmt === 'currency') return `$${value}`;
      return String(value);
    };
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: this.showLegend(),
          position: 'bottom',
          labels: {
            color: tickColor,
            font: { size: 10 },
            boxWidth: 10,
            padding: 8,
          },
        },
        tooltip: {
          backgroundColor: isDark ? '#161b22' : '#ffffff',
          titleColor: isDark ? '#e6edf3' : '#162033',
          bodyColor: isDark ? '#8b949e' : '#5f6f87',
          borderColor: isDark ? '#30363d' : '#d8e0eb',
          borderWidth: 1,
          padding: 8,
          callbacks: {
            label: (ctx) => {
              const useFmt = (ctx.dataset as { _fmt?: KpiValueFormat })._fmt ?? fmt;
              const val = ctx.parsed.y ?? ctx.parsed.x ?? 0;
              const prefix = ctx.dataset.label ? `${ctx.dataset.label}: ` : '';
              if (useFmt === 'currency') return `${prefix}$${val.toFixed(2)}`;
              if (useFmt === 'number') return `${prefix}${val.toLocaleString()}`;
              return `${prefix}${val}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            color: tickColor,
            font: { size: 10 },
            maxRotation: 45,
          },
        },
        y: {
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: {
            color: tickColor,
            font: { size: 10 },
            callback: (val) => tickFmt(val, fmt),
          },
        },
        ...(hasY1
          ? {
              y1: {
                position: 'right' as const,
                beginAtZero: true,
                grid: { drawOnChartArea: false },
                ticks: {
                  color: tickColor,
                  font: { size: 10 },
                  callback: (val) => tickFmt(val, y1Fmt),
                },
              },
            }
          : {}),
      },
    };
  });

  /** Download the chart as a PNG image. */
  exportImage(filename = 'chart'): void {
    const chart = this.chartDirective?.chart;
    if (!chart) return;

    const canvas = chart.canvas;
    if (!canvas) return;

    const dataUrl = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = dataUrl;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
