import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal, ViewEncapsulation } from '@angular/core';
import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AgGridAngular } from 'ag-grid-angular';
import type { ColDef, GridReadyEvent, GridApi } from 'ag-grid-community';
import { ModuleRegistry, AllCommunityModule, ValidationModule, themeQuartz } from 'ag-grid-community';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ExpensesApiService } from '../../services/expenses-api.service';
import type { LedgerTransaction, LedgerSummary, TrialBalance, IncomeStatement, BalanceSheet, ChartAccount } from '../../models/ledger.model';

ModuleRegistry.registerModules([AllCommunityModule, ValidationModule]);

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

  readonly theme = themeQuartz;

  readonly columnDefs: ColDef<LedgerTransaction>[] = [
    {
      field: 'txDate', headerName: 'Fecha', width: 135, sort: 'desc',
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
      cellClass: 'cell-mono cell-date',
    },
    {
      field: 'journalEntryId', headerName: 'Asiento', width: 130, sortable: true,
      cellClass: 'cell-mono cell-journal',
      cellRenderer: (p: any) => {
        const isDebit = p.data.debit > 0;
        const container = document.createElement('span');
        const tag = document.createElement('span');
        tag.className = 'je-tag ' + (isDebit ? 'je-debit' : 'je-credit');
        tag.textContent = isDebit ? 'D' : 'C';
        container.appendChild(tag);
        container.appendChild(document.createTextNode(' ' + (p.value ?? '')));
        return container;
      },
    },
    {
      field: 'accountCode', headerName: 'Cuenta', width: 90, sortable: true, filter: true,
      cellClass: 'cell-mono cell-account',
    },
    {
      field: 'description', headerName: 'Descripción', flex: 1, minWidth: 200,
      sortable: true, filter: true,
      cellRenderer: (p: any) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'cell-desc';
        const label = document.createElement('span');
        label.className = 'desc-label';
        label.textContent = p.value ?? '';
        const sub = document.createElement('span');
        sub.className = 'desc-sub';
        sub.textContent = p.data.guestName ?? '';
        wrapper.appendChild(label);
        wrapper.appendChild(sub);
        return wrapper;
      },
    },
    {
      field: 'costCenter', headerName: 'Ctro. Costo', width: 130, sortable: true, filter: true,
      cellClass: 'cell-cost-center',
    },
    {
      field: 'debit', headerName: 'Débito', width: 115, sortable: true,
      valueFormatter: (p) => p.value ? '$' + p.value.toFixed(2) : '\u2014',
      cellClass: 'cell-mono cell-debit',
    },
    {
      field: 'credit', headerName: 'Crédito', width: 115, sortable: true,
      valueFormatter: (p) => p.value ? '$' + p.value.toFixed(2) : '\u2014',
      cellClass: 'cell-mono cell-credit',
    },
    {
      field: 'balance', headerName: 'Balance', width: 125, sortable: true,
      valueFormatter: (p) => '$' + ((p.value ?? 0) as number).toFixed(2),
      cellClass: 'cell-mono cell-balance',
    },
    {
      field: 'accountingPeriod', headerName: 'Período', width: 90, sortable: true, filter: true,
      cellClass: 'cell-mono cell-period',
    },
    {
      field: 'folioRef', headerName: 'Folio / Factura', width: 140, sortable: true, filter: true,
      cellClass: 'cell-folio',
    },
  ];

  readonly defaultColDef: ColDef = { resizable: true, sortable: true, suppressMovable: true };
  readonly rowClassRules = {
    'row-credit': (p: any) => p.data?.credit > 0,
  };

  getRowId = (params: any) => {
    if (params.data?.id) return String(params.data.id);
    if (params.data?._id) return String(params.data._id);
    return 'row-' + String(params.rowIndex ?? 0);
  };

  constructor() {
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

  private loadAll() {
    const propId = this.selectedPropId();
    if (!propId) return;
    this.loading.set(true);

    this.api.getLedgerSummary(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (s) => this.summary.set(s),
      error: () => this.summary.set(null),
    });

    this.api.getLedgerPeriods(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (periods) => this.availablePeriods.set(periods),
      error: () => this.availablePeriods.set([]),
    });

    this.api.getLedgerTransactions(propId, 1, 100, 'tx_date', 'desc', this.selectedPeriod() || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => { this.rowData.set(data.items); this.loading.set(false); },
      error: () => this.loading.set(false),
    });

    this.api.getTrialBalance(propId, this.selectedPeriod() || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (tb) => this.trialBalance.set(tb),
      error: () => this.trialBalance.set(null),
    });

    this.api.getIncomeStatement(propId, this.selectedPeriod() || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (inc) => this.incomeStatement.set(inc),
      error: () => this.incomeStatement.set(null),
    });

    this.api.getBalanceSheet(propId, this.selectedPeriod() || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (bs) => this.balanceSheet.set(bs),
      error: () => this.balanceSheet.set(null),
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

  // ─── PDF Export ───

  private ts(): string {
    return new Date().toLocaleString('es-MX', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  private fmt(n: number): string {
    return '$' + n.toFixed(2);
  }

  exportIncomeStatementPdf(): void {
    const inc = this.incomeStatement();
    if (!inc) return;

    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pw = doc.internal.pageSize.getWidth();
    const period = inc.period || this.selectedPeriod() || 'Todos los períodos';
    const propLabel = this.selectedLabel() || `Propiedad #${inc.propId}`;

    // Header
    doc.setFontSize(16);
    doc.text('Estado de Resultados (P&L)', pw / 2, 16, { align: 'center' });
    doc.setFontSize(10);
    doc.text(`${propLabel}  |  Período: ${period}`, pw / 2, 24, { align: 'center' });
    doc.text(`Generado: ${this.ts()}`, pw / 2, 30, { align: 'center' });

    const head = [['Cuenta', 'Nombre', 'Débitos', 'Créditos', 'Neto']];
    const headStyles = { fillColor: [22, 101, 52] as [number, number, number], textColor: [255, 255, 255] as [number, number, number], fontStyle: 'bold' as const };

    let y = 38;

    // Revenue
    const revBody = inc.revenue.lines.map(r => [r.accountCode, r.accountName, this.fmt(r.debits), this.fmt(r.credits), this.fmt(r.net)]);
    if (revBody.length === 0) revBody.push(['', 'Sin movimientos', '', '', '']);
    doc.setFontSize(11);
    doc.setTextColor(22, 101, 52);
    doc.text('Ingresos (4xxx)', 14, y);
    y += 5;
    autoTable(doc, { startY: y, head, body: revBody, theme: 'grid', headStyles, styles: { fontSize: 9 }, foot: [['', '', '', 'Total Ingresos', this.fmt(inc.revenue.total)]], footStyles: { fontStyle: 'bold', fillColor: [232, 245, 233] as [number, number, number] } });
    y = (doc as any).lastAutoTable.finalY + 6;

    // Discounts (if any)
    if (inc.discounts.lines.length > 0) {
      const discBody = inc.discounts.lines.map(r => [r.accountCode, r.accountName, this.fmt(r.debits), this.fmt(r.credits), this.fmt(r.net)]);
      doc.setFontSize(11);
      doc.setTextColor(146, 64, 14);
      doc.text('Descuentos / Devoluciones (6xxx)', 14, y);
      y += 5;
      autoTable(doc, { startY: y, head, body: discBody, theme: 'grid', headStyles: { ...headStyles, fillColor: [146, 64, 14] as [number, number, number] }, styles: { fontSize: 9 }, foot: [['', '', '', 'Total Descuentos', this.fmt(inc.discounts.total)]], footStyles: { fontStyle: 'bold', fillColor: [255, 243, 224] as [number, number, number] } });
      y = (doc as any).lastAutoTable.finalY + 6;
    }

    // Net Revenue bar
    doc.setFillColor(240, 253, 244);
    doc.rect(14, y, pw - 28, 7, 'F');
    doc.setFontSize(10);
    doc.setTextColor(22, 101, 52);
    doc.text(`Ingresos Netos: ${this.fmt(inc.revenue.total)} − ${this.fmt(inc.discounts.total)} = ${this.fmt(inc.netRevenue)}`, pw / 2, y + 5, { align: 'center' });
    y += 11;

    // Costs
    const costBody = inc.costs.lines.map(r => [r.accountCode, r.accountName, this.fmt(r.debits), this.fmt(r.credits), this.fmt(r.net)]);
    if (costBody.length === 0) costBody.push(['', 'Sin movimientos', '', '', '']);
    doc.setFontSize(11);
    doc.setTextColor(153, 27, 27);
    doc.text('Costos y Gastos (5xxx)', 14, y);
    y += 5;
    autoTable(doc, { startY: y, head, body: costBody, theme: 'grid', headStyles: { ...headStyles, fillColor: [153, 27, 27] as [number, number, number] }, styles: { fontSize: 9 }, foot: [['', '', '', 'Total Costos', this.fmt(inc.costs.total)]], footStyles: { fontStyle: 'bold', fillColor: [252, 228, 236] as [number, number, number] } });
    y = (doc as any).lastAutoTable.finalY + 8;

    // Net Income
    const isProfit = inc.netIncome >= 0;
    doc.setFillColor(isProfit ? 220 : 254, isProfit ? 252 : 242, isProfit ? 231 : 242);
    doc.rect(14, y, pw - 28, 8, 'F');
    doc.setFontSize(11);
    doc.setTextColor(isProfit ? 22 : 153, isProfit ? 101 : 27, isProfit ? 52 : 27);
    doc.setFont('helvetica', 'bold');
    doc.text(`Resultado Neto del Período: ${this.fmt(inc.netIncome)}`, pw / 2, y + 5.5, { align: 'center' });

    doc.save(`estado-resultados_${propLabel.replace(/\s/g, '_')}_${period}.pdf`);
  }

  exportBalanceSheetPdf(): void {
    const bs = this.balanceSheet();
    if (!bs) return;

    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pw = doc.internal.pageSize.getWidth();
    const period = bs.period || this.selectedPeriod() || 'Todos los períodos';
    const propLabel = this.selectedLabel() || `Propiedad #${bs.propId}`;

    // Header
    doc.setFontSize(16);
    doc.text('Balance General', pw / 2, 16, { align: 'center' });
    doc.setFontSize(10);
    doc.text(`${propLabel}  |  Período: ${period}`, pw / 2, 24, { align: 'center' });
    doc.text(`Generado: ${this.ts()}  |  ${bs.isBalanced ? 'BALANCEADO' : 'DESBALANCEADO'}`, pw / 2, 30, { align: 'center' });

    const head = [['Cuenta', 'Nombre', 'Débitos', 'Créditos', 'Neto']];
    let y = 38;

    // Assets
    const assetBody = bs.assets.lines.map(r => [r.accountCode, r.accountName, this.fmt(r.debits), this.fmt(r.credits), this.fmt(r.net)]);
    if (assetBody.length === 0) assetBody.push(['', 'Sin movimientos', '', '', '']);
    doc.setFontSize(11);
    doc.setTextColor(30, 58, 138);
    doc.text('Activos (1xxx)', 14, y);
    y += 5;
    autoTable(doc, { startY: y, head, body: assetBody, theme: 'grid', headStyles: { fillColor: [30, 58, 138] as [number, number, number], textColor: [255, 255, 255] as [number, number, number], fontStyle: 'bold' }, styles: { fontSize: 9 }, foot: [['', '', '', 'Total Activos', this.fmt(bs.assets.total)]], footStyles: { fontStyle: 'bold', fillColor: [227, 242, 253] as [number, number, number] } });
    y = (doc as any).lastAutoTable.finalY + 6;

    // Liabilities
    const liabBody = bs.liabilities.lines.map(r => [r.accountCode, r.accountName, this.fmt(r.debits), this.fmt(r.credits), this.fmt(r.net)]);
    if (liabBody.length === 0) liabBody.push(['', 'Sin movimientos', '', '', '']);
    doc.setFontSize(11);
    doc.setTextColor(146, 64, 14);
    doc.text('Pasivos (2xxx)', 14, y);
    y += 5;
    autoTable(doc, { startY: y, head, body: liabBody, theme: 'grid', headStyles: { fillColor: [146, 64, 14] as [number, number, number], textColor: [255, 255, 255] as [number, number, number], fontStyle: 'bold' }, styles: { fontSize: 9 }, foot: [['', '', '', 'Total Pasivos', this.fmt(bs.liabilities.total)]], footStyles: { fontStyle: 'bold', fillColor: [254, 243, 199] as [number, number, number] } });
    y = (doc as any).lastAutoTable.finalY + 6;

    // Equity (if any)
    if (bs.equity.lines.length > 0) {
      const eqBody = bs.equity.lines.map(r => [r.accountCode, r.accountName, this.fmt(r.debits), this.fmt(r.credits), this.fmt(r.net)]);
      doc.setFontSize(11);
      doc.setTextColor(106, 27, 154);
      doc.text('Patrimonio (3xxx)', 14, y);
      y += 5;
      autoTable(doc, { startY: y, head, body: eqBody, theme: 'grid', headStyles: { fillColor: [106, 27, 154] as [number, number, number], textColor: [255, 255, 255] as [number, number, number], fontStyle: 'bold' }, styles: { fontSize: 9 }, foot: [['', '', '', 'Total Patrimonio', this.fmt(bs.equity.total)]], footStyles: { fontStyle: 'bold', fillColor: [243, 229, 245] as [number, number, number] } });
      y = (doc as any).lastAutoTable.finalY + 6;
    }

    // Net Income line
    doc.setFillColor(240, 253, 244);
    doc.rect(14, y, pw - 28, 7, 'F');
    doc.setFontSize(10);
    doc.setTextColor(22, 101, 52);
    doc.text(`Resultado del Período: ${this.fmt(bs.netIncome)}`, pw / 2, y + 5, { align: 'center' });
    y += 11;

    // Equation verification
    doc.setFillColor(bs.isBalanced ? 220 : 254, bs.isBalanced ? 252 : 242, bs.isBalanced ? 231 : 242);
    doc.rect(14, y, pw - 28, 8, 'F');
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(bs.isBalanced ? 22 : 153, bs.isBalanced ? 101 : 27, bs.isBalanced ? 52 : 27);
    doc.text(`Pasivos + Patrimonio + Resultado = ${this.fmt(bs.totalLiabilitiesAndEquity)}`, pw / 2, y + 5.5, { align: 'center' });

    doc.save(`balance-general_${propLabel.replace(/\s/g, '_')}_${period}.pdf`);
  }
}
