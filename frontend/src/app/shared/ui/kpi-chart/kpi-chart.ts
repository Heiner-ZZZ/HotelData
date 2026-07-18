import { ChangeDetectionStrategy, Component, computed, input, ViewChild, inject } from '@angular/core';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';
import type { ChartConfiguration, ChartData, ChartType } from 'chart.js';
import { ThemeService } from '../../../core/theme/theme.service';

@Component({
  selector: 'app-kpi-chart',
  imports: [BaseChartDirective],
  providers: [provideCharts(withDefaultRegisterables())],
  template: `
    <div class="kpi-chart-wrap">
      @if (title()) {
        <h3 class="kpi-chart-title">{{ title() }}</h3>
      }
      <div class="chart-container">
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
  styles: [`
    .kpi-chart-wrap {
      background: var(--surface);
      border: 1px solid var(--app-border);
      border-radius: 12px;
      padding: 1rem 1rem 0.5rem;
      transition: background 0.15s ease, border-color 0.15s ease;
    }
    .kpi-chart-title {
      margin: 0 0 0.5rem;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--app-text);
      transition: color 0.15s ease;
    }
    .chart-container {
      position: relative;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KpiChartComponent {
  @ViewChild(BaseChartDirective) private readonly chartDirective?: BaseChartDirective;
  private readonly themeService = inject(ThemeService);

  readonly title = input<string>('');
  readonly labels = input<string[]>([]);
  readonly datasets = input<{ label: string; data: number[]; color?: string }[]>([]);
  readonly type = input<'bar' | 'line'>('bar');
  readonly height = input(200);
  readonly showLegend = input(false);
  readonly formatValue = input<'none' | 'currency' | 'number'>('none');

  readonly chartType = computed((): ChartType => this.type());
  readonly isDark = this.themeService.isDark;

  readonly colors = ['#1463ff', '#22c55e', '#a78bfa', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];

  readonly chartData = computed((): ChartData => {
    const lbls = this.labels();
    const ds = this.datasets();
    return {
      labels: lbls,
      datasets: ds.map((d, i) => ({
        label: d.label,
        data: d.data,
        backgroundColor: d.color || this.colors[i % this.colors.length] + 'cc',
        borderColor: d.color || this.colors[i % this.colors.length],
        borderWidth: 2,
        fill: this.type() === 'line' ? false : undefined,
        tension: 0.3,
        pointRadius: this.type() === 'line' ? 3 : 0,
        pointHoverRadius: 5,
        barPercentage: 0.6,
        categoryPercentage: 0.8,
      })),
    };
  });

  readonly chartOptions = computed((): ChartConfiguration['options'] => {
    const fmt = this.formatValue();
    const isDark = this.isDark();
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: this.showLegend(),
          position: 'bottom',
          labels: {
            color: isDark ? '#8b949e' : '#5f6f87',
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
              const val = ctx.parsed.y ?? ctx.parsed.x ?? 0;
              if (fmt === 'currency') return `$${val.toFixed(2)}`;
              if (fmt === 'number') return val.toLocaleString();
              return String(val);
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            color: isDark ? '#8b949e' : '#5f6f87',
            font: { size: 10 },
            maxRotation: 45,
          },
        },
        y: {
          beginAtZero: true,
          grid: { color: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' },
          ticks: {
            color: isDark ? '#8b949e' : '#5f6f87',
            font: { size: 10 },
            callback: (val) => {
              if (fmt === 'currency') return `$${val}`;
              return val;
            },
          },
        },
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
