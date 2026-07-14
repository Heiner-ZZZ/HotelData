import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { httpResource } from '@angular/common/http';

import { ToastService } from '../../../../shared/services/toast.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { BscViewModel } from '../../models/bsc.model';
import type { BscResponseDto } from '../../models/bsc.dto';
import { mapBscResponse } from '../../mappers/bsc.mapper';

@Component({
  selector: 'app-bsc-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
  ],
  templateUrl: './bsc-page.html',
  styleUrl: './bsc-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BscPageComponent {
  private readonly toast = inject(ToastService);

  readonly bscResource = httpResource<BscViewModel>(() => '/api/kpi/bsc', {
    parse: (dto) => mapBscResponse(dto as BscResponseDto),
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.bscResource.isLoading()) return 'loading';
    if (this.bscResource.error()) return 'error';
    const vm = this.bscResource.value();
    if (!vm) return 'loading';
    return vm.perspectives.length ? 'success' : 'empty';
  });

  readonly errorMessage = computed(() => {
    const err = this.bscResource.error();
    return (err as unknown as ApiError)?.message || '';
  });

  readonly summaryScoreClass = computed(() => {
    const s = this.bscResource.value()?.summary;
    if (!s) return '';
    if (s.score >= 80) return 'score-excellent';
    if (s.score >= 60) return 'score-good';
    if (s.score >= 40) return 'score-fair';
    return 'score-critical';
  });

  onRetry() {
    this.bscResource.reload();
  }

  exportReport(): void {
    const vm = this.bscResource.value();
    if (!vm) return;

    const rows: string[][] = [];
    for (const p of vm.perspectives) {
      rows.push([`[${p.label}]`, '', '', '', '', '']);
      for (const k of p.kpis) {
        rows.push([k.label, k.value, k.target, k.pctChange, k.semaforo.toUpperCase(), k.detail]);
      }
      rows.push(['', '', '', '', '', '']);
    }

    const headers = ['Indicador', 'Valor Actual', 'Meta', 'Variación', 'Estado', 'Detalle'];
    const csvContent = [
      `Balanced Scorecard - HotelData Hub`,
      `Período: ${vm.periodLabel}`,
      `Puntaje: ${vm.summary.score}% (${vm.summary.label})`,
      '',
      headers.join(','),
      ...rows.map((r) => r.map((c) => `"${c}"`).join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bsc-report-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    this.toast.show('Reporte BSC exportado como CSV.', 'info', 4000);
  }
}
