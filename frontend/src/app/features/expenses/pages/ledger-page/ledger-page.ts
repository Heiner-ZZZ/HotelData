import { ChangeDetectionStrategy, Component, computed, effect, HostListener, inject, signal, untracked, ViewEncapsulation } from '@angular/core';
import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { AgGridAngular } from 'ag-grid-angular';
import type {
  ColDef,
  GridReadyEvent,
  GridApi,
  ColumnHeaderClickedEvent,
  RowClassParams,
  GetRowIdParams,
  ICellRendererParams,
} from 'ag-grid-community';
import { ModuleRegistry, AllCommunityModule, ValidationModule, themeQuartz } from 'ag-grid-community';
import { ActivatedRoute } from '@angular/router';

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
import { ExpensesApiService, DEFAULT_LEDGER_PAGE_SIZE } from '../../services/expenses-api.service';
import type { LedgerTransaction, LedgerSummary, TrialBalance, IncomeStatement, BalanceSheet, ChartAccount } from '../../models/ledger.model';
import type { LedgerSummaryDto, TrialBalanceDto, IncomeStatementDto, BalanceSheetDto, LedgerTransactionsDto, ChartAccountDto } from '../../models/ledger.dto';
import { mapLedgerSummary, mapTrialBalance, mapIncomeStatement, mapBalanceSheet, mapLedgerTransactions, mapChartAccounts } from '../../mappers/expenses.mapper';

ModuleRegistry.registerModules([AllCommunityModule, ValidationModule]);

/** Synthetic group row inserted into the flat array for journal-entry grouping. */
interface JournalEntryGroupRow extends LedgerTransaction {
  __groupRow: true;
  __childCount: number;
  __groupDebit: number;
  __groupCredit: number;
}

/** Module-scope helper hoisted from the 2 XLSX export implementations.
 *
 * NOTE: declared as a `type` alias (was `type` locally too). Using `interface`
 * here would cause TS2322 against `ExcelSheetPayload.headers`
 * ({ label: string; [style: string]: unknown }[]) — TS treats `interface` with
 * known-key-only fields as a stricter shape than an index-signature target,
 * while `type` aliases are erased and surface as compatible. Keep as `type`.
 */
type HeaderCell = {
  label: string;
  align?: 'left' | 'right' | 'center';
};

/** Module-scope helper hoisted from the 2 XLSX export implementations. */
type Row = (string | number | null)[];

/**
 * Sibling interface that narrows `__isChild` to the literal `true` for rows
 * emitted by `rebuildTreeData` as journal-entry-expansion children. The base
 * `LedgerTransaction` keeps the field optional (`?: boolean`) so unrelated
 * fetches (summary, periods, etc.) don't carry the marker spuriously.
 */
interface LedgerTransactionExpanded extends LedgerTransaction {
  __isChild: true;
}

type TreeRow = LedgerTransaction | JournalEntryGroupRow | LedgerTransactionExpanded;

/**
 * Coerce any incoming value into a finite number.
 *
 * Used by ledger valueFormatters and the P&L waterfall template to defend
 * against string-number wire values (e.g. Mongo Decimal128 serialized as
 * "10.50") and undefined/null fields that would otherwise crash `.toFixed(2)`.
 *
 * Returns:
 * - finite numbers → unchanged
 * - finite numeric strings ("10.50", "0") → coerced via Number()
 * - everything else (null, undefined, NaN, Infinity, objects, booleans) → 0
 *
 * Pure function; safe to hoist to module scope and reuse.
 */
const _num = (v: unknown): number => {
  if (typeof v === 'number') return Number.isFinite(v) ? v : 0;
  if (typeof v === 'string') {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
};

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
  private readonly route = inject(ActivatedRoute);
  readonly ctx = inject(PropertyContextService);
  private readonly reports = inject(ReportsExportService);

  /** URL query param snapshot for initial load. */
  private readonly qp = toSignal(this.route.queryParamMap, { initialValue: this.route.snapshot.queryParamMap });
  readonly urlPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');
  readonly selectedPeriod = signal('');
  readonly gridApi = signal<GridApi | null>(null);

  readonly summary = signal<LedgerSummary | null>(null);
  readonly trialBalance = signal<TrialBalance | null>(null);
  readonly showTrialBalance = signal(false);
  readonly incomeStatement = signal<IncomeStatement | null>(null);
  readonly showIncomeStatement = signal(false);
  readonly balanceSheet = signal<BalanceSheet | null>(null);
  readonly showBalanceSheet = signal(false);
  readonly availablePeriods = signal<string[]>([]);
  readonly chartAccounts = signal<Map<string, ChartAccount>>(new Map());
  readonly selectedColumnId = signal<string | null>(null);
  readonly pinnedColumns = signal<{ left: string[]; right: string[] }>({ left: [], right: [] });
  readonly groupedMode = signal(true);
  readonly treeData = signal<TreeRow[]>([]);
  readonly expandedGroups = signal<Set<string>>(new Set());
  readonly rowData = signal<LedgerTransaction[]>([]);
  readonly columnsDropdownOpen = signal(false);
  readonly columnVisibility = signal<Record<string, boolean>>({});
  readonly loading = signal(false);

  /** Has the user manually toggled any group's expansion? */
  private expansionUserTouched = false;

  // ═══ Data resources — httpResource (replaces all manual GETs in loadAll) ═══

  readonly summaryResource = httpResource<LedgerSummary>(() => {
    const propId = this.selectedPropId();
    return propId ? `/api/expenses/ledger/${propId}/summary` : undefined;
  }, {
    parse: (dto) => mapLedgerSummary(dto as LedgerSummaryDto),
  });

  readonly periodsResource = httpResource<string[]>(() => {
    const propId = this.selectedPropId();
    return propId ? `/api/expenses/ledger/${propId}/periods` : undefined;
  });

  readonly transactionsResource = httpResource<LedgerTransaction[]>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    const period = this.selectedPeriod() || undefined;
    let url = `/api/expenses/ledger/${propId}/transactions?page=1&page_size=${DEFAULT_LEDGER_PAGE_SIZE}&sort_by=tx_date&sort_dir=desc`;
    if (period) url += `&period=${period}`;
    return url;
  }, {
    parse: (dto) => mapLedgerTransactions(dto as LedgerTransactionsDto),
  });

  readonly trialBalanceResource = httpResource<TrialBalance>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    const period = this.selectedPeriod() || undefined;
    let url = `/api/expenses/ledger/${propId}/trial-balance`;
    if (period) url += `?period=${period}`;
    return url;
  }, {
    parse: (dto) => mapTrialBalance(dto as TrialBalanceDto),
  });

  readonly incomeStatementResource = httpResource<IncomeStatement>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    const period = this.selectedPeriod() || undefined;
    let url = `/api/expenses/ledger/${propId}/income-statement`;
    if (period) url += `?period=${period}`;
    return url;
  }, {
    parse: (dto) => mapIncomeStatement(dto as IncomeStatementDto),
  });

  readonly balanceSheetResource = httpResource<BalanceSheet>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    const period = this.selectedPeriod() || undefined;
    let url = `/api/expenses/ledger/${propId}/balance-sheet`;
    if (period) url += `?period=${period}`;
    return url;
  }, {
    parse: (dto) => mapBalanceSheet(dto as BalanceSheetDto),
  });

  readonly chartOfAccountsResource = httpResource<ChartAccount[]>(() => `/api/expenses/ledger/chart-of-accounts`, {
    parse: (dto) => mapChartAccounts(dto as ChartAccountDto[]),
  });

  /**
   * ag-grid theme with semantic CSS-variable lookups so a `[data-theme="dark"]`
   * flip on the document swaps the surface/text/border tokens automatically.
   * themeQuartz (v36) without withParams() defaults to its internal light
   * constants and ignores app-level theme context.
   */
  readonly theme = themeQuartz.withParams({
    backgroundColor: 'var(--surface)',
    foregroundColor: 'var(--app-text)',
    headerBackgroundColor: 'var(--surface-soft)',
    headerTextColor: 'var(--app-text)',
    rowHoverColor: 'var(--surface-hover)',
    borderColor: 'var(--app-border)',
    cellTextColor: 'var(--app-text)',
    rowBorder: { color: 'var(--app-border)', style: 'solid', width: 1 },
    oddRowBackgroundColor: 'var(--surface-raised)',
    selectedRowBackgroundColor: 'color-mix(in srgb, var(--accent) 8%, transparent)',
  });

  /**
   * Template-scope alias for the module-scope `_num` helper. Angular templates
   * can read `public` and `protected` members, but with `strictTemplates: true`
   * (Angular 22 default), `protected` produces a TS2341 compile error in the
   * template type-check phase. We expose it as `public` here so the template
   * binds cleanly without sacrificing encapsulation concerns in callers — the
   * template legitimately needs the helper and `public readonly` matches.
   *
   * Used by ledger-page.html to wrap every `' + X.toFixed(2)` expression with
   * `_num(X).toFixed(2)` so string-number inputs cannot crash the renderer.
   */
  public readonly _num = _num;

  columnDefs!: ColDef<LedgerTransaction>[];

  readonly defaultColDef: ColDef = {
    resizable: true,
    sortable: true,
    suppressMovable: true,
    suppressSizeToFit: false,
  };
  readonly rowClassRules = {
    'row-credit': (p: RowClassParams<LedgerTransaction>) => (p.data?.credit ?? 0) > 0,
    'je-group-row': (p: RowClassParams<TreeRow>) => p.data?.__groupRow === true,
    'je-child-row': (p: RowClassParams<TreeRow>) => p.data?.__isChild === true,
  };

  /**
   * Every row leaves `rebuildTreeData` with a deterministic `id` (see the
   * stable-id policy in that method), so this method no longer needs a
   * non-deterministic counter fallback. The contract: same logical doc
   * yields the same id across renders — ag-grid reconciles nodes correctly.
   */
  getRowId = (params: GetRowIdParams<TreeRow>) => {
    const d = params.data;
    if (!d) return '';
    return String(d.id ?? '');
  };

  constructor() {
    this.columnDefs = this.buildColumnDefs();

    // Prefer URL query param ?prop_id= for direct navigation;
    // fall back to PropertyContextService for cross-page navigation.
    const urlPropId = this.urlPropId();
    const ctxPropId = this.ctx.currentPropId();
    if (urlPropId) {
      this.selectedPropId.set(urlPropId);
      this.selectedLabel.set(this.ctx.currentPropLabel() || `Propiedad #${urlPropId}`);
      this.ctx.setProperty(urlPropId, this.selectedLabel());
    } else if (ctxPropId) {
      this.selectedPropId.set(ctxPropId);
      this.selectedLabel.set(this.ctx.currentPropLabel());
    }

    // ═══ Reactive effects (replace manual loadAll() + subscriptions) ═══

    // 1. Sync URL ↔ selectedPropId
    effect(() => {
      const urlPid = this.urlPropId();
      if (urlPid && urlPid !== this.selectedPropId()) {
        untracked(() => {
          this.selectedPropId.set(urlPid);
          this.selectedLabel.set(this.ctx.currentPropLabel() || `Propiedad #${urlPid}`);
          this.ctx.setProperty(urlPid, this.selectedLabel());
        });
      }
    });

    // 2. Reset UI state when prop or period changes
    effect(() => {
      // Track both signals to trigger the reset
      const _pid = this.selectedPropId();
      const _period = this.selectedPeriod();
      void _pid; void _period;
      if (!_pid) return;
      untracked(() => {
        this.expandedGroups.set(new Set());
        this.expansionUserTouched = false;
      });
    });

    // 3. Map resource values to component signals
    effect(() => {
      const s = this.summaryResource.value();
      if (s !== undefined) untracked(() => this.summary.set(s));
    });

    effect(() => {
      const p = this.periodsResource.value();
      if (p) untracked(() => this.availablePeriods.set(p));
    });

    effect(() => {
      const t = this.transactionsResource.value();
      if (t !== undefined) {
        untracked(() => {
          this.rebuildTreeData(t);
          this.autoSizeGridColumns();
        });
      }
    });

    effect(() => {
      const tb = this.trialBalanceResource.value();
      if (tb !== undefined) untracked(() => this.trialBalance.set(tb));
    });

    effect(() => {
      const inc = this.incomeStatementResource.value();
      if (inc !== undefined) untracked(() => this.incomeStatement.set(inc));
    });

    effect(() => {
      const bs = this.balanceSheetResource.value();
      if (bs !== undefined) untracked(() => this.balanceSheet.set(bs));
    });

    effect(() => {
      const accounts = this.chartOfAccountsResource.value();
      if (accounts) {
        untracked(() => {
          const map = new Map<string, ChartAccount>();
          for (const a of accounts) map.set(a.accountCode, a);
          this.chartAccounts.set(map);
        });
      }
    });

    // 4. Loading state aggregated from all resources
    effect(() => {
      const loading = this.summaryResource.isLoading()
        || this.periodsResource.isLoading()
        || this.transactionsResource.isLoading()
        || this.trialBalanceResource.isLoading()
        || this.incomeStatementResource.isLoading()
        || this.balanceSheetResource.isLoading()
        || this.chartOfAccountsResource.isLoading();
      untracked(() => this.loading.set(loading));
    });
  }

  // ─── Column definitions ───

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
        cellRenderer: (p: ICellRendererParams<LedgerTransaction>) => this.renderJournalCell(p),
      },
      {
        field: 'accountCode', headerName: 'Cuenta', minWidth: 80, sortable: true, filter: true,
        headerClass: 'col-even', cellClass: 'cell-mono cell-account col-even',
      },
      {
        field: 'description', headerName: 'Descripción', minWidth: 220,
        sortable: true, filter: true,
        headerClass: 'col-odd',
        cellRenderer: (p: ICellRendererParams<TreeRow>) => {
          if (p.data?.__groupRow === true) return '';
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
        valueFormatter: (p) => {
          const n = _num(p.value);
          return n ? '$' + n.toFixed(2) : '\u2014';
        },
        cellClass: 'cell-mono cell-debit col-odd',
      },
      {
        field: 'credit', headerName: 'Crédito', minWidth: 105, sortable: true,
        headerClass: 'col-even',
        valueFormatter: (p) => {
          const n = _num(p.value);
          return n ? '$' + n.toFixed(2) : '\u2014';
        },
        cellClass: 'cell-mono cell-credit col-even',
      },
      {
        field: 'balance', headerName: 'Balance', minWidth: 115, sortable: true,
        headerClass: 'col-odd',
        valueFormatter: (p) => '$' + _num(p.value).toFixed(2),
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

  private renderJournalCell(p: ICellRendererParams<TreeRow>): HTMLElement {
    if (p.data?.__groupRow === true) return this.renderGroupRowCell(p.data as JournalEntryGroupRow);
    return this.renderLeafRowCell(p as ICellRendererParams<LedgerTransaction>);
  }

  private renderGroupRowCell(data: JournalEntryGroupRow): HTMLElement {
    const jeId = data.journalEntryId || '';
    const isExpanded = this.expandedGroups().has(jeId);
    const wrapper = document.createElement('div');
    wrapper.className = 'cell-group-row';

    const chev = document.createElement('span');
    chev.className = 'group-chevron';
    chev.textContent = isExpanded ? '\u25BC' : '\u25B6';
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
    const usd = (n: unknown) => '$' + _num(n).toFixed(2);
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

  private renderLeafRowCell(p: ICellRendererParams<LedgerTransaction>): HTMLElement {
    const isDebit = (p.data?.debit ?? 0) > 0;
    const container = document.createElement('span');
    const tag = document.createElement('span');
    tag.className = 'je-tag ' + (isDebit ? 'je-debit' : 'je-credit');
    tag.textContent = isDebit ? 'D' : 'C';
    container.appendChild(tag);
    container.appendChild(document.createTextNode(' ' + (p.value ?? '')));
    return container;
  }

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

  onPropSelected(event: { propId: number; label: string }) {
    this.selectedPropId.set(event.propId);
    this.selectedLabel.set(event.label);
    this.ctx.setProperty(event.propId, event.label);
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

  onFilterChange(event: Event) {
    this.gridApi()?.setGridOption('quickFilterText', (event.target as HTMLInputElement).value);
  }

  onPeriodChange(event: Event) {
    this.selectedPeriod.set((event.target as HTMLSelectElement).value);
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

    const fmtDate = (v: string | number | Date | null | undefined): string => {
      if (!v) return '';
      const d = new Date(v);
      if (isNaN(d.getTime())) return String(v).slice(0, 10);
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      return `${day}-${month} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    };
    const usd = (n: unknown) => '$' + _num(n).toFixed(2);
    const esc = (v: string | number | null | undefined) => {
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

  // ─── Tree builder ───

  private rebuildTreeData(flatItems?: LedgerTransaction[]): void {
    const items = flatItems ?? [...this.rowData()];
    if (!items.length) {
      this.rowData.set([]);
      this.treeData.set([]);
      return;
    }

    // ─── Stable-id policy ───
    // Required: ag-grid uses `getRowId` to reconcile nodes across renders.
    // Every row must leave this builder with a deterministic id so the grid
    // never collapses two distinct rows. Precedence per row:
    //   1. server-provided `id` (api response);
    //   2. Mongo `_id` (string form);
    //   3. content composite `<jeId>|<accountCode>|<txDate>|<debit>|<credit>`.
    // Group rows get a synthetic `__ledger_grp__<jeId>` id (stable per JE).
    const stableIdFor = (r: LedgerTransaction): string =>
      r.id || r._id || `${r.journalEntryId}|${r.accountCode}|${r.txDate}|${r.debit}|${r.credit}`;
    const withIds: LedgerTransaction[] = items.map((r) => ({ ...r, id: stableIdFor(r) }));
    this.rowData.set(withIds);

    if (!this.groupedMode()) {
      // Non-grouped mode: hand the same stable-ided rows straight to ag-grid.
      this.treeData.set(withIds);
      return;
    }

    const sorted = [...items].sort((a, b) => {
      const jeA = a.journalEntryId || '';
      const jeB = b.journalEntryId || '';
      if (jeA !== jeB) return jeB.localeCompare(jeA);
      return new Date(b.txDate).getTime() - new Date(a.txDate).getTime();
    });

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
        // Cover the previous "undefined children" AG Grid crash: any virtualizer
        // or row-buffer that inspects node.children.length sees an empty arr.
        children: [],
        __childCount: groupBuffer.length,
        __groupDebit: groupBuffer.reduce((s, r) => s + (r.debit || 0), 0),
        __groupCredit: groupBuffer.reduce((s, r) => s + (r.credit || 0), 0),
        id: '__ledger_grp__' + jeId,
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
          // `child` already carries a stable id from the policy above; cast
          // to `LedgerTransactionExpanded` because `__isChild: true` matches
          // the narrowed literal type defined in the sibling interface.
          visible.push({ ...child, __isChild: true } as LedgerTransactionExpanded);
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

  accountTooltip(code: string): string {
    const acct = this.chartAccounts().get(code);
    if (!acct) return code;
    const nb = acct.normalBalance === 'debit' ? 'Deudor' : acct.normalBalance === 'credit' ? 'Acreedor' : acct.normalBalance;
    return `${acct.accountName}\nSaldo normal: ${nb}\n${acct.description}`;
  }

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
    const head: HeaderCell[] = [
      { label: 'Cuenta' },
      { label: 'Nombre de la cuenta' },
      { label: 'Débitos', align: 'right' },
      { label: 'Créditos', align: 'right' },
      { label: 'Neto', align: 'right' },
    ];
    const summaryItems = [
      { label: 'Ingresos brutos', val: inc.revenue.total },
      { label: 'Descuentos', val: -inc.discounts.total },
      { label: 'Ingresos netos', val: inc.netRevenue },
      { label: 'Costos y gastos', val: -inc.costs.total },
      { label: 'Resultado del período', val: inc.netIncome },
    ];
    await this.reports.exportXlsx({
      filename,
      sheet_title: `${propLabel} · Estado de Resultados · ${period}`,
      sheets: [
        {
          name: 'Resumen',
          headers: [{ label: 'Métrica' }, { label: 'Total' }],
          rows: summaryItems.map<Row>((s) => [s.label, s.val]),
          column_widths: { A: 36, B: 22 },
        },
        {
          name: 'Ingresos (4xxx)',
          headers: head,
          rows: [
            ...inc.revenue.lines.map<Row>((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net]),
            ['Total Ingresos', '', '', '', inc.revenue.total],
          ],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
        {
          name: 'Descuentos (6xxx)',
          headers: head,
          rows: inc.discounts.lines.length
            ? [
                ...inc.discounts.lines.map<Row>((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net]),
                ['Total Descuentos', '', '', '', inc.discounts.total],
              ]
            : [],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
        {
          name: 'Costos (5xxx)',
          headers: head,
          rows: [
            ...inc.costs.lines.map<Row>((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net]),
            ['Total Costos', '', '', '', inc.costs.total],
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
    const head: HeaderCell[] = [
      { label: 'Cuenta' },
      { label: 'Nombre de la cuenta' },
      { label: 'Débitos', align: 'right' },
      { label: 'Créditos', align: 'right' },
      { label: 'Neto', align: 'right' },
    ];
    await this.reports.exportXlsx({
      filename,
      sheet_title: `${propLabel} · Balance General · ${period}`,
      sheets: [
        {
          name: 'Resumen',
          headers: [{ label: 'Métrica' }, { label: 'Total', align: 'right' }],
          rows: [
            ['Total activos', bs.assets.total],
            ['Total pasivos', bs.liabilities.total],
            ['Patrimonio', bs.equity.total],
            ['Resultado del período', bs.netIncome],
            ['Pasivos + Patrimonio + Resultado', bs.totalLiabilitiesAndEquity],
            ['Estado', bs.isBalanced ? 'BALANCEADO' : 'DESBALANCEADO'],
          ],
          column_widths: { A: 38, B: 22 },
        },
        {
          name: 'Activos (1xxx)',
          headers: head,
          rows: [
            ...bs.assets.lines.map<Row>((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net]),
            ['Total', '', '', '', bs.assets.total],
          ],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
        {
          name: 'Pasivos (2xxx)',
          headers: head,
          rows: [
            ...bs.liabilities.lines.map<Row>((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net]),
            ['Total', '', '', '', bs.liabilities.total],
          ],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
        {
          name: 'Patrimonio (3xxx)',
          headers: head,
          rows: bs.equity.lines.length
            ? [
                ...bs.equity.lines.map<Row>((r) => [r.accountCode, r.accountName, r.debits, r.credits, r.net]),
                ['Total', '', '', '', bs.equity.total],
              ]
            : [],
          column_widths: { A: 14, B: 40, C: 18, D: 18, E: 18 },
        },
      ],
    });
  }
}
