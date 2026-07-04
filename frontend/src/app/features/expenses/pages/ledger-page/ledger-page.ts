import { ChangeDetectionStrategy, Component, DestroyRef, HostListener, inject, signal, ViewEncapsulation } from '@angular/core';
import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AgGridAngular } from 'ag-grid-angular';
import type { ColDef, GridReadyEvent, GridApi, ColumnHeaderClickedEvent } from 'ag-grid-community';
import { ModuleRegistry, AllCommunityModule, ValidationModule, themeQuartz } from 'ag-grid-community';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ReportsExportService } from '../../../../shared/services/reports-export.service';
import {
  buildReportShell,
  buildSummaryGrid,
  buildTable,
  fmtUsd,
} from '../../../../shared/utils/report-html-templates';
import { ExpensesApiService } from '../../services/expenses-api.service';
import type { LedgerTransaction, LedgerSummary, TrialBalance, IncomeStatement, BalanceSheet, ChartAccount } from '../../models/ledger.model';

ModuleRegistry.registerModules([AllCommunityModule, ValidationModule]);

/** Synthetic group row inserted into the flat array for journal-entry grouping. */
interface JournalEntryGroupRow extends LedgerTransaction {
  __groupRow: true;
  __childCount: number;
  __groupDebit: number;
  __groupCredit: number;
}

type TreeRow = LedgerTransaction | JournalEntryGroupRow;

@Component({
  selector: 'app-ledger-page',
  standalone: true,
  imports: [AgGridAngular, PageHeaderComponent, PropertySelectorComponent, CurrencyPipe, DecimalPipe],
  templateUrl: './ledger-page.html',
  styleUrl: './ledger-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class LedgerPageComponent {
  private readonly api = inject(ExpensesApiService);
  private readonly destroyRef = inject(DestroyRef);
  readonly ctx = inject(PropertyContextService);
  private readonly reports = inject(ReportsExportService);

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');
  readonly gridApi = signal<GridApi | null>(null);

  readonly rowData = signal<LedgerTransaction[]>([]);
  readonly summary = signal<LedgerSummary | null>(null);
  readonly trialBalance = signal<TrialBalance | null>(null);
  readonly showTrialBalance = signal(false);
  readonly incomeStatement = signal<IncomeStatement | null>(null);
  readonly showIncomeStatement = signal(false);
  readonly balanceSheet = signal<BalanceSheet | null>(null);
  readonly showBalanceSheet = signal(false);
  readonly selectedPeriod = signal('');
  readonly availablePeriods = signal<string[]>([]);
  readonly loading = signal(false);
  readonly chartAccounts = signal<Map<string, ChartAccount>>(new Map());
  readonly selectedColumnId = signal<string | null>(null);
  readonly pinnedColumns = signal<{ left: string[]; right: string[] }>({ left: [], right: [] });
  readonly groupedMode = signal(true);
  /** Visible rows after grouping + per-JE expansion filtering. Community-only. */
  readonly treeData = signal<TreeRow[]>([]);
  /** Set of journalEntryIds that are currently expanded. Empty before first load. */
  readonly expandedGroups = signal<Set<string>>(new Set());

  /** Column visibility dropdown state. */
  readonly columnsDropdownOpen = signal(false);
  /** Map of colId → visible (true=shown, false=hidden). */
  readonly columnVisibility = signal<Record<string, boolean>>({});

  readonly theme = themeQuartz;

  /** Has the user manually toggled any group's expansion? Once true, we
   *  stop auto-expanding new JE groups on data reload. */
  private expansionUserTouched = false;

  /** Declarations declared as `!` so the cellRenderer closures can call
   *  back into the component (this.toggleGroupExpansion, etc.). Built
   *  in the constructor. */
  columnDefs!: ColDef<LedgerTransaction>[];

  readonly defaultColDef: ColDef = {
    resizable: true,
    sortable: true,
    suppressMovable: true,
    suppressSizeToFit: false,
  };
  readonly rowClassRules = {
    'row-credit': (p: any) => p.data?.credit > 0,
    'je-group-row': (p: any) => p.data?.__groupRow === true,
    'je-child-row': (p: any) => p.data?.__isChild === true,
  };

  getRowId = (params: any) => {
    if (params.data?.id) return String(params.data.id);
    if (params.data?._id) return String(params.data._id);
    return 'row-' + String(params.rowIndex ?? 0);
  };

  constructor() {
    this.columnDefs = this.buildColumnDefs();

    const propId = this.ctx.currentPropId();
    if (propId) {
      this.selectedPropId.set(propId);
      this.selectedLabel.set(this.ctx.currentPropLabel());
      this.loadAll();
    }
  }

  // ─── Column definitions (constructed so cellRenderer has `this`) ───

  private buildColumnDefs(): ColDef<LedgerTransaction>[] {
    return [
      {
        field: 'txDate', headerName: 'Fecha', minWidth: 125, sort: 'desc',
        headerClass: 'col-even', cellClass: 'cell-mono cell-date col-even',
        valueFormatter: (p) => {
          const d = new Date(p.value);
          if (isNaN(d.getTime())) {
            const fallback = new Date(p.value + 'T00:00:00');
            if (isNaN(fallback.getTime())) return (p.value ?? '').slice(0, 10);
            const fd = fallback.getDate().toString().padStart(2, '0');
            const fm = (fallback.getMonth() + 1).toString().padStart(2, '0');
            return fd + '-' + fm + ' 00:00';
          }
          const day = String(d.getDate()).padStart(2, '0');
          const month = String(d.getMonth() + 1).padStart(2, '0');
          return day + '-' + month + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
        },
      },
      {
        field: 'journalEntryId', headerName: 'Asiento', minWidth: 420, sortable: true,
        headerClass: 'col-odd', cellClass: 'cell-mono cell-journal col-odd',
        cellRenderer: (p: any) => this.renderJournalCell(p),
      },
      {
        field: 'accountCode', headerName: 'Cuenta', minWidth: 80, sortable: true, filter: true,
        headerClass: 'col-even', cellClass: 'cell-mono cell-account col-even',
      },
      {
        field: 'description', headerName: 'Descripción', minWidth: 220,
        sortable: true, filter: true,
        headerClass: 'col-odd',
        cellRenderer: (p: any) => {
          // Skip the expensive renderer for synthetic group rows (their description is empty).
          if (p.data?.__groupRow) return '';
          const wrapper = document.createElement('div');
          wrapper.className = 'cell-desc col-odd';
          const label = document.createElement('span');
          label.className = 'desc-label';
          label.textContent = p.value ?? '';
          const sub = document.createElement('span');
          sub.className = 'desc-sub';
          sub.textContent = p.data?.guestName ?? '';
          wrapper.appendChild(label);
          wrapper.appendChild(sub);
          return wrapper;
        },
      },
      {
        field: 'costCenter', headerName: 'Ctro. Costo', minWidth: 110, sortable: true, filter: true,
        headerClass: 'col-even', cellClass: 'cell-cost-center col-even',
      },
      {
        field: 'debit', headerName: 'Débito', minWidth: 105, sortable: true,
        headerClass: 'col-odd',
        valueFormatter: (p) => p.value ? '$' + p.value.toFixed(2) : '\u2014',
        cellClass: 'cell-mono cell-debit col-odd',
      },
      {
        field: 'credit', headerName: 'Crédito', minWidth: 105, sortable: true,
        headerClass: 'col-even',
        valueFormatter: (p) => p.value ? '$' + p.value.toFixed(2) : '\u2014',
        cellClass: 'cell-mono cell-credit col-even',
      },
      {
        field: 'balance', headerName: 'Balance', minWidth: 115, sortable: true,
        headerClass: 'col-odd',
        valueFormatter: (p) => '$' + ((p.value ?? 0) as number).toFixed(2),
        cellClass: 'cell-mono cell-balance col-odd',
      },
      {
        field: 'accountingPeriod', headerName: 'Período', minWidth: 85, sortable: true, filter: true,
        headerClass: 'col-even', cellClass: 'cell-mono cell-period col-even',
      },
      {
        field: 'folioRef', headerName: 'Folio / Factura', minWidth: 135, sortable: true, filter: true,
        headerClass: 'col-odd', cellClass: 'cell-folio col-odd',
      },
    ];
  }

  /** Renderer for the journal-entry column. Branches on data.__groupRow to
   *  show chevron + JE pill for synthetic groups, and the existing
   *  D/C tag + jeId for leaf rows. */
  private renderJournalCell(p: any): HTMLElement {
    if (p.data?.__groupRow) return this.renderGroupRowCell(p.data as JournalEntryGroupRow);
    return this.renderLeafRowCell(p);
  }

  private renderGroupRowCell(data: JournalEntryGroupRow): HTMLElement {
    const jeId = data.journalEntryId || '';
    const isExpanded = this.expandedGroups().has(jeId);
    const wrapper = document.createElement('div');
    wrapper.className = 'cell-group-row';

    const chev = document.createElement('span');
    chev.className = 'group-chevron';
    chev.textContent = isExpanded ? '\u25BC' : '\u25B6'; // ▼ / ▶
    chev.title = isExpanded ? 'Contraer hijos' : 'Expandir hijos';
    chev.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleGroupExpansion(jeId);
    });
    wrapper.appendChild(chev);

    const jeSpan = document.createElement('span');
    jeSpan.className = 'group-je-id mono';
    jeSpan.textContent = jeId;
    wrapper.appendChild(jeSpan);

    const childBadge = document.createElement('span');
    childBadge.className = 'group-child-badge';
    childBadge.textContent = `${data.__childCount} movs`;
    wrapper.appendChild(childBadge);

    const pill = document.createElement('span');
    pill.className = 'group-dc-pill';
    const usd = (n: number) => '$' + n.toFixed(2);
    const dLabel = document.createElement('span');
    dLabel.className = 'group-dc-debit';
    dLabel.textContent = 'D: ' + usd(data.__groupDebit || 0);
    const sep = document.createElement('span');
    sep.className = 'group-dc-sep';
    sep.textContent = '|';
    const cLabel = document.createElement('span');
    cLabel.className = 'group-dc-credit';
    cLabel.textContent = 'C: ' + usd(data.__groupCredit || 0);
    pill.appendChild(dLabel);
    pill.appendChild(sep);
    pill.appendChild(cLabel);
    wrapper.appendChild(pill);
    return wrapper;
  }

  private renderLeafRowCell(p: any): HTMLElement {
    const isDebit = p.data?.debit > 0;
    const container = document.createElement('span');
    const tag = document.createElement('span');
    tag.className = 'je-tag ' + (isDebit ? 'je-debit' : 'je-credit');
    tag.textContent = isDebit ? 'D' : 'C';
    container.appendChild(tag);
    container.appendChild(document.createTextNode(' ' + (p.value ?? '')));
    return container;
  }

  // ─── Expansion logic ───

  /** Toggle expansion of a single JE group. Rebuilds treeData so the
   *  grid picks up the visibility change via AG Grid's reactive
   *  rowData binding. */
  toggleGroupExpansion(jeId: string): void {
    if (!jeId) return;
    const next = new Set(this.expandedGroups());
    if (next.has(jeId)) {
      next.delete(jeId);
    } else {
      next.add(jeId);
    }
    this.expandedGroups.set(next);
    this.expansionUserTouched = true;
    this.rebuildTreeData();
  }

  // ─── Standard event handlers / column utilities (unchanged) ───

  onPropSelected(event: { propId: number; label: string }) {
    this.selectedPropId.set(event.propId);
    this.selectedLabel.set(event.label);
    this.ctx.setProperty(event.propId, event.label);
    this.loadAll();
  }

  onGridReady(params: GridReadyEvent) {
    this.gridApi.set(params.api);
    this.autoSizeGridColumns();
    setTimeout(() => this.syncPinnedState(), 200);
  }

  onColumnHeaderClicked(event: ColumnHeaderClickedEvent) {
    const column = event.column;
    if ('getColId' in column) {
      this.selectedColumnId.set(column.getColId());
    }
  }

  pinColumnLeft() {
    const api = this.gridApi();
    const colId = this.selectedColumnId();
    if (!api || !colId) return;
    api.setColumnsPinned([colId], 'left');
    this.syncPinnedState();
    this.autoSizeGridColumns();
  }

  pinColumnRight() {
    const api = this.gridApi();
    const colId = this.selectedColumnId();
    if (!api || !colId) return;
    api.setColumnsPinned([colId], 'right');
    this.syncPinnedState();
    this.autoSizeGridColumns();
  }

  resetColumnPins() {
    const api = this.gridApi();
    if (!api) return;
    const cols = api.getAllGridColumns();
    if (cols) {
      for (const col of cols) {
        if (col.getPinned()) {
          api.setColumnsPinned([col.getColId()], null);
        }
      }
    }
    this.pinnedColumns.set({ left: [], right: [] });
    this.autoSizeGridColumns();
  }

  private syncPinnedState() {
    const api = this.gridApi();
    if (!api) return;
    const state = api.getColumnState();
    if (!state) return;
    const left = state.filter(c => c.pinned === 'left').map(c => c.colId);
    const right = state.filter(c => c.pinned === 'right').map(c => c.colId);
    this.pinnedColumns.set({ left, right });
    const vis: Record<string, boolean> = {};
    for (const c of state) {
      if (c.colId !== 'ag-Grid-AutoColumn') {
        vis[c.colId] = !c.hide;
      }
    }
    this.columnVisibility.set(vis);
  }

  toggleColumnsDropdown(): void {
    this.columnsDropdownOpen.update(v => !v);
  }

  toggleColumnVisibility(colId: string): void {
    const api = this.gridApi();
    if (!api) return;
    const current = this.columnVisibility()[colId] ?? true;
    const newVis = !current;
    api.setColumnsVisible([colId], newVis);
    this.columnVisibility.update(v => ({ ...v, [colId]: newVis }));
    this.columnsDropdownOpen.set(false);
    this.autoSizeGridColumns();
  }

  @HostListener('document:click', ['$event'])
  closeColumnsDropdown(event: Event): void {
    if (!this.columnsDropdownOpen()) return;
    const target = event.target as HTMLElement;
    if (!target.closest('.col-vis-toggle') && !target.closest('.col-vis-dropdown')) {
      this.columnsDropdownOpen.set(false);
    }
  }

  private autoSizeGridColumns() {
    const api = this.gridApi();
    if (!api) return;
    setTimeout(() => {
      const allColumnIds = api.getAllGridColumns()?.map(c => c.getColId()) ?? [];
      if (allColumnIds.length > 0) {
        api.autoSizeColumns(allColumnIds);
      }
    }, 150);
  }

  private loadAll() {
    const propId = this.selectedPropId();
    if (!propId) return;
    this.loading.set(true);
    // Drop stale expansion state whenever data reloads. Without this, JEs
    // added by a new period filter would silently default to collapsed,
    // and toggles from a previous hotel would carry over.
    this.expandedGroups.set(new Set());
    this.expansionUserTouched = false;

    this.api.getLedgerSummary(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (s) => this.summary.set(s),
      error: (err) => { console.error('[Ledger] Failed to load summary', err); this.summary.set(null); },
    });

    this.api.getLedgerPeriods(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (periods) => this.availablePeriods.set(periods),
      error: (err) => { console.error('[Ledger] Failed to load periods', err); this.availablePeriods.set([]); },
    });

    this.api.getLedgerTransactions(propId, 1, 100, 'tx_date', 'desc', this.selectedPeriod() || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => {
        this.rebuildTreeData(data.items);
        this.loading.set(false);
        this.autoSizeGridColumns();
      },
      error: (err) => { console.error('[Ledger] Failed to load transactions', err); this.loading.set(false); },
    });

    this.api.getTrialBalance(propId, this.selectedPeriod() || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (tb) => this.trialBalance.set(tb),
      error: (err) => { console.error('[Ledger] Failed to load trial balance', err); this.trialBalance.set(null); },
    });

    this.api.getIncomeStatement(propId, this.selectedPeriod() || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (inc) => this.incomeStatement.set(inc),
      error: (err) => { console.error('[Ledger] Failed to load income statement', err); this.incomeStatement.set(null); },
    });

    this.api.getBalanceSheet(propId, this.selectedPeriod() || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (bs) => this.balanceSheet.set(bs),
      error: (err) => { console.error('[Ledger] Failed to load balance sheet', err); this.balanceSheet.set(null); },
    });

    this.api.getChartOfAccounts().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (accounts) => {
        const map = new Map<string, ChartAccount>();
        for (const a of accounts) map.set(a.accountCode, a);
        this.chartAccounts.set(map);
      },
    });
  }

  onFilterChange(event: Event) {
    this.gridApi()?.setGridOption('quickFilterText', (event.target as HTMLInputElement).value);
  }

  onPeriodChange(event: Event) {
    this.selectedPeriod.set((event.target as HTMLSelectElement).value);
    this.loadAll();
  }

  toggleTrialBalance() {
    this.showTrialBalance.update(v => !v);
  }

  toggleIncomeStatement() {
    this.showIncomeStatement.update(v => !v);
  }

  toggleBalanceSheet() {
    this.showBalanceSheet.update(v => !v);
  }

  toggleRowGrouping() {
    this.groupedMode.set(!this.groupedMode());
    this.rebuildTreeData();
  }

  // ─── CSV Export ───

  exportLedgerCsv(): void {
    const gridApi = this.gridApi();
    if (!gridApi) return;

    const rows: string[][] = [];
    const header = ['Fecha', 'DC', 'Asiento', 'Cuenta', 'Descripción', 'Huésped', 'Ctro. Costo', 'Débito', 'Crédito', 'Balance', 'Período', 'Folio / Factura'];
    rows.push(header);

    const fmtDate = (v: any): string => {
      if (!v) return '';
      const d = new Date(v);
      if (isNaN(d.getTime())) return String(v).slice(0, 10);
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      return `${day}-${month} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    };
    const usd = (n: number) => '$' + n.toFixed(2);
    const esc = (v: any) => {
      if (v === null || v === undefined) return '';
      const s = String(v);
      return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
    };

    gridApi.forEachNodeAfterFilterAndSort((node) => {
      const d = node.data as TreeRow | undefined;
      if (!d) return;
      const isGroup = (d as JournalEntryGroupRow).__groupRow;
      if (isGroup) {
        const g = d as JournalEntryGroupRow;
        rows.push([
          '', '', esc(g.journalEntryId), '',
          `JE ${g.journalEntryId} — ${g.__childCount} movs`,
          '', '',
          g.__groupDebit ? usd(g.__groupDebit) : '',
          g.__groupCredit ? usd(g.__groupCredit) : '',
          usd(g.__groupDebit - g.__groupCredit),
          '', '',
        ]);
        rows.push([]);
      } else {
        rows.push([
          fmtDate(d.txDate),
          d.debit > 0 ? 'D' : 'C',
          esc(d.journalEntryId),
          esc(d.accountCode),
          esc(d.description),
          esc(d.guestName),
          esc(d.costCenter),
          d.debit ? usd(d.debit) : '',
          d.credit ? usd(d.credit) : '',
          usd(d.balance ?? 0),
          esc(d.accountingPeriod),
          esc(d.folioRef),
        ]);
      }
    });

    const csv = rows.map(r => r.join(',')).join('\n');
    const bom = '\uFEFF';
    const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const propLabel = this.selectedLabel().replace(/\s+/g, '_') || 'ledger';
    const period = this.selectedPeriod() || 'todos';
    a.download = `libro-mayor_${propLabel}_${period}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ─── Tree (grouped view) builder ───

  private rebuildTreeData(flatItems?: LedgerTransaction[]): void {
    const items = flatItems ?? [...this.rowData()];
    if (!items.length) {
      this.rowData.set([]);
      this.treeData.set([]);
      return;
    }
    this.rowData.set(items);

    if (!this.groupedMode()) {
      this.treeData.set([]);
      return;
    }

    const sorted = [...items].sort((a, b) => {
      const jeA = a.journalEntryId || '';
      const jeB = b.journalEntryId || '';
      if (jeA !== jeB) return jeB.localeCompare(jeA);
      return new Date(b.txDate).getTime() - new Date(a.txDate).getTime();
    });

    // Auto-expand everything on first load. After the user starts
    // toggling, their preferences are preserved.
    if (!this.expansionUserTouched) {
      const allJEs = new Set<string>();
      for (const row of sorted) {
        if (row.journalEntryId) allJEs.add(row.journalEntryId);
      }
      this.expandedGroups.set(allJEs);
    }

    const expanded = this.expandedGroups();
    const visible: TreeRow[] = [];
    let currentJE = '';
    let groupBuffer: LedgerTransaction[] = [];

    const flushGroup = () => {
      if (groupBuffer.length === 0) return;
      const first = groupBuffer[0];
      const jeId = first.journalEntryId || '';
      visible.push({
        ...first,
        __groupRow: true,
        __childCount: groupBuffer.length,
        __groupDebit: groupBuffer.reduce((s, r) => s + (r.debit || 0), 0),
        __groupCredit: groupBuffer.reduce((s, r) => s + (r.credit || 0), 0),
        // Distinctive ID prefix to avoid collisions with real `_id` values
        // (especially important for ObjectIds from MongoDB transactions).
        id: ('__ledger_grp__' + jeId) as any,
        accountCode: '',
        description: '',
        debit: 0,
        credit: 0,
        balance: 0,
        costCenter: '',
        folioRef: '',
        guestName: '',
      } as JournalEntryGroupRow);
      if (expanded.has(jeId)) {
        for (const child of groupBuffer) {
          visible.push({ ...child, __isChild: true } as any);
        }
      }
      groupBuffer = [];
    };

    for (const row of sorted) {
      const je = row.journalEntryId || '';
      if (je !== currentJE) {
        flushGroup();
        currentJE = je;
      }
      groupBuffer.push(row);
    }
    flushGroup();

    this.treeData.set(visible);
  }

  // ─── Tooltip helpers ───

  accountTooltip(code: string): string {
    const acct = this.chartAccounts().get(code);
    if (!acct) return code;
    const nb = acct.normalBalance === 'debit' ? 'Deudor' : acct.normalBalance === 'credit' ? 'Acreedor' : acct.normalBalance;
    return `${acct.accountName}\nSaldo normal: ${nb}\n${acct.description}`;
  }

  // ─── P&L Bar Chart helpers ───

  pnlBarPct(value: number): number {
    const inc = this.incomeStatement();
    if (!inc) return 0;
    const absVal = value < 0 ? -value : value;
    const max = Math.max(inc.revenue.total, inc.discounts.total, inc.costs.total, inc.netIncome < 0 ? -inc.netIncome : inc.netIncome, 1);
    return Math.min(100, Math.round((absVal / max) * 100));
  }

  // ─── Export (WeasyPrint PDF + OpenPyXL XLSX) ───

  private ts(): string {
    return new Date().toLocaleString('es-MX', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  private fmt(n: number): string {
    return fmtUsd(n);
  }

  private async safeExport(action: () => Promise<void>): Promise<void> {
    try {
      await action();
    } catch (err) {
      console.error('[Ledger] Export failed', err);
    }
  }

  exportIncomeStatementPdf(): void {
    void this.safeExport(() => this.exportIncomeStatementPdfImpl());
  }

  exportBalanceSheetPdf(): void {
    void this.safeExport(() => this.exportBalanceSheetPdfImpl());
  }

  exportIncomeStatementXlsx(): void {
    void this.safeExport(() => this.exportIncomeStatementXlsxImpl());
  }

  exportBalanceSheetXlsx(): void {
    void this.safeExport(() => this.exportBalanceSheetXlsxImpl());
  }

  private async exportIncomeStatementPdfImpl(): Promise<void> {
    const inc = this.incomeStatement();
    if (!inc) return;
    const period = inc.period || this.selectedPeriod() || 'Todos los períodos';
    const propLabel = this.selectedLabel() || `Propiedad #${inc.propId}`;
    const filename = `estado-resultados_${propLabel.replace(/\s+/g, '_')}_${period.replace(/\s+/g, '_')}`.toLowerCase();

    const netTone = inc.netIncome >= 0 ? 'positive' : 'negative';
    const grid = buildSummaryGrid([
      { label: 'Ingresos brutos', value: fmtUsd(inc.revenue.total), tone: inc.revenue.total > 0 ? 'positive' : 'neutral' },
      { label: 'Descuentos', value: fmtUsd(inc.discounts.total), tone: inc.discounts.total > 0 ? 'warning' : 'neutral' },
      { label: 'Ingresos netos', value: fmtUsd(inc.netRevenue), tone: inc.netRevenue > 0 ? 'positive' : 'neutral' },
      { label: 'Costos y gastos', value: fmtUsd(inc.costs.total), tone: inc.costs.total > 0 ? 'negative' : 'neutral' },
      { label: 'Resultado del período', value: fmtUsd(inc.netIncome), tone: netTone, sub: inc.netIncome >= 0 ? 'UTILIDAD' : 'PÉRDIDA' },
    ]);

    const revTable = buildTable(
      [
        { label: 'Cuenta', align: 'left' },
        { label: 'Nombre', align: 'left' },
        { label: 'Débitos', align: 'right', cssClass: 'num' },
        { label: 'Créditos', align: 'right', cssClass: 'num' },
        { label: 'Neto', align: 'right', cssClass: 'num positive' },
      ],
      inc.revenue.lines.map((r) => [r.accountCode, r.accountName, fmtUsd(r.debits), fmtUsd(r.credits), fmtUsd(r.net, { showZero: true })]),
      ['', '', '', 'Total Ingresos', fmtUsd(inc.revenue.total, { showZero: true })]
    );

    const discTable = inc.discounts.lines.length
      ? buildTable(
          [
            { label: 'Cuenta', align: 'left' },
            { label: 'Nombre', align: 'left' },
            { label: 'Débitos', align: 'right', cssClass: 'num' },
            { label: 'Créditos', align: 'right', cssClass: 'num' },
            { label: 'Neto', align: 'right', cssClass: 'num negative' },
          ],
          inc.discounts.lines.map((r) => [r.accountCode, r.accountName, fmtUsd(r.debits), fmtUsd(r.credits), fmtUsd(r.net, { showZero: true })]),
          ['', '', '', 'Total Descuentos', fmtUsd(inc.discounts.total, { showZero: true })]
        )
      : '';

    const netRevEq = `<div class="eq-bar"><span class="label">Ingresos Netos (${fmtUsd(inc.revenue.total)} − ${fmtUsd(inc.discounts.total)})</span><span class="value">${fmtUsd(inc.netRevenue)}</span></div>`;

    const costTable = buildTable(
      [
        { label: 'Cuenta', align: 'left' },
        { label: 'Nombre', align: 'left' },
        { label: 'Débitos', align: 'right', cssClass: 'num' },
        { label: 'Créditos', align: 'right', cssClass: 'num' },
        { label: 'Neto', align: 'right', cssClass: 'num negative' },
      ],
      inc.costs.lines.map((r) => [r.accountCode, r.accountName, fmtUsd(r.debits), fmtUsd(r.credits), fmtUsd(r.net, { showZero: true })]),
      ['', '', '', 'Total Costos', fmtUsd(inc.costs.total, { showZero: true })]
    );

    const bottomLines = `
      <div class="eq-bar ${netTone === 'positive' ? 'success' : 'danger'}">
        <span class="label">Resultado Neto del Período</span>
        <span class="value">${fmtUsd(inc.netIncome)}</span>
      </div>
      <p style="font-size: 9pt; color: var(--c-text-muted); text-align: center; margin-top: 4mm;">
        ${inc.netIncome >= 0 ? '🟢 El hotel generó utilidad durante este período.' : '🔴 El hotel registró pérdida durante este período — requiere atención.'}
      </p>`;

    const bodyHtml = `
      ${grid}
      <h2>Ingresos (4xxx)</h2>
      ${revTable}
      ${discTable ? `<h2 class="page-break">Descuentos / Devoluciones (6xxx)</h2>${discTable}` : ''}
      ${netRevEq}
      <h2 class="page-break">Costos y Gastos (5xxx)</h2>
      ${costTable}
      ${bottomLines}
    `;

    const html = buildReportShell({
      title: 'Estado de Resultados (P&L)',
      subtitle: `${propLabel} · ${period}`,
      generatedAt: new Date(),
      metaRows: [
        { label: 'Propiedad', value: propLabel },
        { label: 'Período', value: period },
        { label: 'Resultado', value: `${fmtUsd(inc.netIncome)} (${inc.netIncome >= 0 ? 'UTILIDAD' : 'PÉRDIDA'})` },
        { label: 'Generado', value: this.ts() },
      ],
      bodyHtml,
    });
    await this.reports.exportPdf(html, filename, 'Estado de Resultados (P&L)');
  }

  private async exportIncomeStatementXlsxImpl(): Promise<void> {
    const inc = this.incomeStatement();
    if (!inc) return;
    const period = inc.period || this.selectedPeriod() || 'Todos los períodos';
    const propLabel = this.selectedLabel() || `Propiedad #${inc.propId}`;
    const filename = `estado-resultados_${propLabel.replace(/\s+/g, '_')}_${period.replace(/\s+/g, '_')}`.toLowerCase();
    const head = [
      { label: 'Cuenta' },
      { label: 'Nombre de la cuenta' },
      { label: 'Débitos', align: 'right' } as any,
      { label: 'Créditos', align: 'right' } as any,
      { label: 'Neto', align: 'right' } as any,
    ];
    const summary = [
      { label: 'Ingresos brutos' },
      { label: 'Descuentos' },
      { label: 'Ingresos netos' },
      { label: 'Costos y gastos' },
      { label: 'Resultado del período' },
    ];
    const totals = [inc.revenue.total, -inc.discounts.total, inc.netRevenue, -inc.costs.total, inc.netIncome];
    await this.reports.exportXlsx({
      filename,
      sheet_title: `${propLabel} · Estado de Resultados · ${period}`,
      sheets: [
        {
          name: 'Resumen',
          headers: [{ label: 'Métrica' }, { label: 'Total' }],
          rows: summary.map((s, i) => [s.label, totals[i]]),
          column_widths: { A: 36, B: 22 },
        },
        {
          name: 'Ingresos (4xxx)',
          headers: head,
          rows: [
            ...inc.revenue.lines.map((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net] as any),
            ['Total Ingresos', '', '', '', inc.revenue.total] as any,
          ],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
        {
          name: 'Descuentos (6xxx)',
          headers: head,
          rows: inc.discounts.lines.length
            ? [
                ...inc.discounts.lines.map((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net] as any),
                ['Total Descuentos', '', '', '', inc.discounts.total] as any,
              ]
            : [],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
        {
          name: 'Costos (5xxx)',
          headers: head,
          rows: [
            ...inc.costs.lines.map((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net] as any),
            ['Total Costos', '', '', '', inc.costs.total] as any,
          ],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
      ],
    });
  }

  private async exportBalanceSheetPdfImpl(): Promise<void> {
    const bs = this.balanceSheet();
    if (!bs) return;
    const period = bs.period || this.selectedPeriod() || 'Todos los períodos';
    const propLabel = this.selectedLabel() || `Propiedad #${bs.propId}`;
    const filename = `balance-general_${propLabel.replace(/\s+/g, '_')}_${period.replace(/\s+/g, '_')}`.toLowerCase();

    const grid = buildSummaryGrid([
      { label: 'Total activos', value: fmtUsd(bs.assets.total), tone: 'neutral' },
      { label: 'Total pasivos', value: fmtUsd(bs.liabilities.total), tone: bs.liabilities.total > 0 ? 'warning' : 'neutral' },
      { label: 'Patrimonio', value: fmtUsd(bs.equity.total) },
      { label: 'Resultado del período', value: fmtUsd(bs.netIncome), tone: bs.netIncome >= 0 ? 'positive' : 'negative' },
      { label: 'Ecuación contable', value: bs.isBalanced ? 'BALANCEADO' : 'DESBALANCEADO', tone: bs.isBalanced ? 'positive' : 'negative' },
    ]);

    const assetTable = buildTable(
      [
        { label: 'Cuenta', align: 'left' },
        { label: 'Nombre', align: 'left' },
        { label: 'Débitos', align: 'right', cssClass: 'num' },
        { label: 'Créditos', align: 'right', cssClass: 'num' },
        { label: 'Neto', align: 'right', cssClass: 'num' },
      ],
      bs.assets.lines.map((r) => [r.accountCode, r.accountName, fmtUsd(r.debits), fmtUsd(r.credits), fmtUsd(r.net, { showZero: true })]),
      ['', '', '', 'Total Activos', fmtUsd(bs.assets.total, { showZero: true })]
    );

    const liabTable = buildTable(
      [
        { label: 'Cuenta', align: 'left' },
        { label: 'Nombre', align: 'left' },
        { label: 'Débitos', align: 'right', cssClass: 'num' },
        { label: 'Créditos', align: 'right', cssClass: 'num' },
        { label: 'Neto', align: 'right', cssClass: 'num' },
      ],
      bs.liabilities.lines.map((r) => [r.accountCode, r.accountName, fmtUsd(r.debits), fmtUsd(r.credits), fmtUsd(r.net, { showZero: true })]),
      ['', '', '', 'Total Pasivos', fmtUsd(bs.liabilities.total, { showZero: true })]
    );

    const eqTable = bs.equity.lines.length
      ? buildTable(
          [
            { label: 'Cuenta', align: 'left' },
            { label: 'Nombre', align: 'left' },
            { label: 'Débitos', align: 'right', cssClass: 'num' },
            { label: 'Créditos', align: 'right', cssClass: 'num' },
            { label: 'Neto', align: 'right', cssClass: 'num' },
          ],
          bs.equity.lines.map((r) => [r.accountCode, r.accountName, fmtUsd(r.debits), fmtUsd(r.credits), fmtUsd(r.net, { showZero: true })]),
          ['', '', '', 'Total Patrimonio', fmtUsd(bs.equity.total, { showZero: true })]
        )
      : '';

    const eqCheck =
      `<div class="eq-bar ${bs.isBalanced ? 'success' : 'danger'}">` +
      `<span class="label">Pasivos + Patrimonio + Resultado</span>` +
      `<span class="value">${fmtUsd(bs.totalLiabilitiesAndEquity)}</span>` +
      `</div>` +
      `<p style="font-size: 9pt; color: var(--c-text-muted); text-align: center; margin-top: 4mm;">` +
      `Ecuación contable: ${bs.isBalanced ? '✓ BALANCEADO' : '⚠ DESBALANCEADO — requiere revisión'}.` +
      `</p>`;

    const resultLine =
      `<div class="eq-bar">` +
      `<span class="label">Resultado del período</span>` +
      `<span class="value">${fmtUsd(bs.netIncome)}</span>` +
      `</div>`;

    const bodyHtml = `
      ${grid}
      <h2>Activos (1xxx)</h2>
      ${assetTable}
      <h2 class="page-break">Pasivos (2xxx)</h2>
      ${liabTable}
      ${eqTable ? `<h2>Patrimonio (3xxx)</h2>${eqTable}` : ''}
      ${resultLine}
      ${eqCheck}
    `;

    const html = buildReportShell({
      title: 'Balance General',
      subtitle: `${propLabel} · ${period} · ${bs.isBalanced ? 'BALANCEADO' : 'DESBALANCEADO'}`,
      generatedAt: new Date(),
      metaRows: [
        { label: 'Propiedad', value: propLabel },
        { label: 'Período', value: period },
        { label: 'Estado', value: bs.isBalanced ? 'BALANCEADO' : 'DESBALANCEADO' },
        { label: 'Generado', value: this.ts() },
      ],
      bodyHtml,
    });
    await this.reports.exportPdf(html, filename, 'Balance General');
  }

  private async exportBalanceSheetXlsxImpl(): Promise<void> {
    const bs = this.balanceSheet();
    if (!bs) return;
    const period = bs.period || this.selectedPeriod() || 'Todos los períodos';
    const propLabel = this.selectedLabel() || `Propiedad #${bs.propId}`;
    const filename = `balance-general_${propLabel.replace(/\s+/g, '_')}_${period.replace(/\s+/g, '_')}`.toLowerCase();
    const head = [
      { label: 'Cuenta' },
      { label: 'Nombre de la cuenta' },
      { label: 'Débitos', align: 'right' } as any,
      { label: 'Créditos', align: 'right' } as any,
      { label: 'Neto', align: 'right' } as any,
    ];
    await this.reports.exportXlsx({
      filename,
      sheet_title: `${propLabel} · Balance General · ${period}`,
      sheets: [
        {
          name: 'Resumen',
          headers: [{ label: 'Métrica' }, { label: 'Total', align: 'right' } as any],
          rows: [
            ['Total activos', bs.assets.total] as any,
            ['Total pasivos', bs.liabilities.total] as any,
            ['Patrimonio', bs.equity.total] as any,
            ['Resultado del período', bs.netIncome] as any,
            ['Pasivos + Patrimonio + Resultado', bs.totalLiabilitiesAndEquity] as any,
            ['Estado', (bs.isBalanced ? 'BALANCEADO' : 'DESBALANCEADO')] as any,
          ],
          column_widths: { A: 38, B: 22 },
        },
        {
          name: 'Activos (1xxx)',
          headers: head,
          rows: [
            ...bs.assets.lines.map((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net] as any),
            ['Total', '', '', '', bs.assets.total] as any,
          ],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
        {
          name: 'Pasivos (2xxx)',
          headers: head,
          rows: [
            ...bs.liabilities.lines.map((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net] as any),
            ['Total', '', '', '', bs.liabilities.total] as any,
          ],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
        {
          name: 'Patrimonio (3xxx)',
          headers: head,
          rows: bs.equity.lines.length
            ? [
                ...bs.equity.lines.map((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net] as any),
                ['Total', '', '', '', bs.equity.total] as any,
              ]
            : [],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
      ],
    });
  }
}
