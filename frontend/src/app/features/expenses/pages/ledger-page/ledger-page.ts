import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal, computed } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { AgGridAngular } from 'ag-grid-angular';
import type { ColDef, GridReadyEvent, GridApi, ITooltipParams } from 'ag-grid-community';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ExpensesApiService } from '../../services/expenses-api.service';
import type { LedgerTransaction, LedgerFolio, LedgerSummary } from '../../models/ledger.model';

ModuleRegistry.registerModules([AllCommunityModule]);

@Component({
  selector: 'app-ledger-page',
  standalone: true,
  imports: [AgGridAngular, CurrencyPipe, DatePipe, PageHeaderComponent, PropertySelectorComponent],
  templateUrl: './ledger-page.html',
  styleUrl: './ledger-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerPageComponent {
  private readonly api = inject(ExpensesApiService);
  private readonly destroyRef = inject(DestroyRef);
  readonly ctx = inject(PropertyContextService);

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');
  readonly gridApi = signal<GridApi | null>(null);

  readonly summary = signal<LedgerSummary | null>(null);
  readonly folios = signal<LedgerFolio[]>([]);
  readonly selectedFolio = signal<LedgerFolio | null>(null);
  readonly loading = signal(false);

  readonly columnDefs: ColDef<LedgerTransaction>[] = [
    {
      field: 'txDate', headerName: 'Fecha', width: 120, sort: 'desc',
      valueFormatter: (p) => {
        const d = new Date(p.value + 'T00:00:00');
        if (isNaN(d.getTime())) return p.value?.slice(0, 10) ?? '';
        const day = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        return `${day}-${month} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
      },
      cellClass: 'cell-mono cell-date',
    },
    {
      field: 'folioRef', headerName: 'Folio', width: 100, sortable: true, filter: true,
      cellClass: 'cell-folio',
    },
    {
      field: 'description', headerName: 'Descripción / Cuenta', flex: 1, minWidth: 200,
      sortable: true, filter: true,
      cellRenderer: (p: any) => {
        return `<div class="cell-desc">
          <span class="desc-label">${p.value}</span>
          <span class="desc-code">${p.data.accountCode}</span>
        </div>`;
      },
    },
    {
      field: 'debit', headerName: 'Débito', width: 110, sortable: true,
      valueFormatter: (p) => p.value ? `$${p.value.toFixed(2)}` : '—',
      cellClass: 'cell-mono cell-debit',
      headerClass: 'header-right',
    },
    {
      field: 'credit', headerName: 'Crédito', width: 110, sortable: true,
      valueFormatter: (p) => p.value ? `$${p.value.toFixed(2)}` : '—',
      cellClass: 'cell-mono cell-credit',
      headerClass: 'header-right',
    },
    {
      field: 'balance', headerName: 'Balance', width: 120, sortable: true,
      valueFormatter: (p) => `$${(p.value ?? 0).toFixed(2)}`,
      cellClass: 'cell-mono cell-balance',
      headerClass: 'header-right',
    },
    {
      field: 'user', headerName: 'Usuario', width: 100, sortable: true, filter: true,
      cellClass: 'cell-mono cell-user',
    },
    {
      field: 'status', headerName: 'Estado', width: 120, sortable: true, filter: true,
      cellRenderer: (p: any) => {
        const statusMap: Record<string, { label: string; css: string }> = {
          audited: { label: 'Auditado', css: 'badge-audited' },
          pending: { label: 'Pendiente', css: 'badge-pending' },
          discrepancy: { label: 'Discrepancia', css: 'badge-discrepancy' },
        };
        const s = statusMap[p.value] || { label: p.value, css: '' };
        return `<span class="status-badge ${s.css}">${s.label}</span>`;
      },
    },
  ];

  readonly defaultColDef: ColDef = {
    resizable: true,
    sortable: true,
    suppressMovable: true,
  };

  readonly rowClassRules = {
    'row-discrepancy': (params: any) => params.data?.status === 'discrepancy',
  };

  constructor() {
    // Auto-load when single-hotel context is ready
    const propId = this.ctx.currentPropId();
    if (propId) {
      this.selectedPropId.set(propId);
      this.selectedLabel.set(this.ctx.currentPropLabel());
      this.loadAll();
    }
  }

  onPropSelected(event: { propId: number; label: string }) {
    this.selectedPropId.set(event.propId);
    this.selectedLabel.set(event.label);
    this.ctx.setProperty(event.propId, event.label);
    this.loadAll();
  }

  onGridReady(params: GridReadyEvent) {
    this.gridApi.set(params.api);
    params.api.sizeColumnsToFit();
  }

  onRowClicked(event: any) {
    const folioRef = event.data?.folioRef;
    if (folioRef) {
      const folio = this.folios().find(f => f.folioRef === folioRef);
      this.selectedFolio.set(folio || null);
    }
  }

  private loadAll() {
    const propId = this.selectedPropId();
    if (!propId) return;
    this.loading.set(true);

    this.api.getLedgerSummary(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (s) => this.summary.set(s),
      error: () => {},
    });

    this.api.getLedgerFolios(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (f) => this.folios.set(f.items),
      error: () => {},
    });

    this.api.getLedgerTransactions(propId, 1, 100).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => this.loading.set(false),
      error: () => this.loading.set(false),
    });
  }

  onFilterChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const api = this.gridApi();
    if (api) {
      api.setGridOption('quickFilterText', input.value);
    }
  }
}
