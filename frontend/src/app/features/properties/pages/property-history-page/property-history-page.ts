import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { filter, map } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ReportsExportService } from '../../../../shared/services/reports-export.service';
import {
  buildReportShell,
  buildSummaryGrid,
  buildTable,
} from '../../../../shared/utils/report-html-templates';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ChangeRecordDto, PropertyHistoryResponseDto } from '../../models/properties.dto';
import { PropertiesApiService } from '../../services/properties-api.service';

/** Helper: extract a runtime error message without `any`.
 *
 * Handles: `Error` instances, plain strings, and duck-typed objects with a
 * string `message` field (covers Angular's `HttpErrorResponse`, XHR errors,
 * and any other framework-neutrally typed error).
 */
function toErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  if (typeof err === 'object' && err !== null && 'message' in err) {
    const msg = (err as { message: unknown }).message;
    if (typeof msg === 'string') return msg;
  }
  return fallback;
}

@Component({
  selector: 'app-property-history-page',
  imports: [DatePipe, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, EmptyStateComponent, ReactiveFormsModule, RouterLink],
  templateUrl: './property-history-page.html',
  styleUrl: './property-history-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PropertyHistoryPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(PropertiesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  private readonly reports = inject(ReportsExportService);

  readonly viewState = signal<ViewState>('loading');
  readonly propId = signal(0);
  readonly displayName = signal('');
  readonly items = signal<ChangeRecordDto[]>([]);
  readonly pagination = signal<PropertyHistoryResponseDto['pagination'] | null>(null);
  readonly filterOptions = signal<{ fields: string[]; users: string[] }>({ fields: [], users: [] });
  readonly selectedChange = signal<ChangeRecordDto | null>(null);
  readonly showDetail = signal(false);
  readonly detailLoading = signal(false);
  readonly detailError = signal('');
  readonly exportingPdf = signal(false);
  readonly exportingXlsx = signal(false);

  readonly filterForm = this.fb.nonNullable.group({
    from: [''],
    to: [''],
    field: [''],
    user: [''],
  });

  constructor() {
    this.route.paramMap
      .pipe(
        map((params) => Number(params.get('propertyId'))),
        filter((pid) => Number.isFinite(pid) && pid > 0),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((pid) => {
        this.propId.set(pid);
        this.loadHistory();
      });

    this.route.queryParamMap
      .pipe(
        filter(() => this.propId() > 0),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(() => {
        this.loadHistory();
      });
  }

  private buildParams(): Record<string, string | number> {
    const qp = this.route.snapshot.queryParamMap;
    const fv = this.filterForm.getRawValue();
    const params: Record<string, string | number> = {};
    const from = qp.get('from') || fv.from;
    const to = qp.get('to') || fv.to;
    const field = qp.get('field') || fv.field;
    const user = qp.get('user') || fv.user;
    const page = Number(qp.get('page') || '1');
    if (from) params['from'] = from;
    if (to) params['to'] = to;
    if (field) params['field'] = field;
    if (user) params['user'] = user;
    if (page > 1) params['page'] = page;
    return params;
  }

  loadHistory(): void {
    const pid = this.propId();
    if (!pid) return;
    this.viewState.set('loading');
    const params = this.buildParams();
    this.api.getPropertyHistory(pid, params).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => {
        this.items.set(res.data);
        this.pagination.set(res.pagination);
        this.filterOptions.set(res.filters);
        const qp = this.route.snapshot.queryParamMap;
        this.filterForm.patchValue({
          from: qp.get('from') ?? '',
          to: qp.get('to') ?? '',
          field: qp.get('field') ?? '',
          user: qp.get('user') ?? '',
        }, { emitEvent: false });
        this.viewState.set(res.data.length ? 'success' : 'empty');
      },
      error: () => this.viewState.set('error'),
    });
  }

  applyFilters(): void {
    const fv = this.filterForm.getRawValue();
    const params = new URLSearchParams();
    if (fv.from) params.set('from', fv.from);
    if (fv.to) params.set('to', fv.to);
    if (fv.field) params.set('field', fv.field);
    if (fv.user) params.set('user', fv.user);
    const qs = params.toString();
    const url = `/management/properties/${this.propId()}/history${qs ? '?' + qs : ''}`;
    window.history.replaceState(null, '', url);
    this.loadHistory();
  }

  clearFilters(): void {
    this.filterForm.reset();
    const url = `/management/properties/${this.propId()}/history`;
    window.history.replaceState(null, '', url);
    this.loadHistory();
  }

  goToPage(page: number): void {
    const qp = this.route.snapshot.queryParamMap;
    const params = new URLSearchParams();
    if (qp.get('from')) params.set('from', qp.get('from')!);
    if (qp.get('to')) params.set('to', qp.get('to')!);
    if (qp.get('field')) params.set('field', qp.get('field')!);
    if (qp.get('user')) params.set('user', qp.get('user')!);
    if (page > 1) params.set('page', String(page));
    const qs = params.toString();
    const url = `/management/properties/${this.propId()}/history${qs ? '?' + qs : ''}`;
    window.history.replaceState(null, '', url);
    this.loadHistory();
  }

  openDetail(change: ChangeRecordDto): void {
    this.selectedChange.set(change);
    this.showDetail.set(true);
    this.detailLoading.set(true);
    this.detailError.set('');
    this.api.getChangeDetail(this.propId(), change.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (detail) => {
        this.selectedChange.set({ ...change, ...detail });
        this.detailLoading.set(false);
      },
      error: () => {
        this.detailError.set('No se pudo cargar el detalle completo.');
        this.detailLoading.set(false);
      },
    });
  }

  closeDetail(): void {
    this.showDetail.set(false);
    this.selectedChange.set(null);
  }

  async exportPdf(): Promise<void> {
    this.exportingPdf.set(true);
    try {
      const pid = this.propId();
      const items = this.items();
      const pag = this.pagination();
      const fv = this.filterForm.getRawValue();
      const fieldsModified = [...new Set(items.map((i: ChangeRecordDto) => i.field))];
      const usersInvolved = [...new Set(items.map((i: ChangeRecordDto) => i.changed_by))];

      const grid = buildSummaryGrid([
        { label: 'Total de cambios', value: String(pag?.total ?? items.length), tone: 'neutral' },
        { label: 'En esta página', value: String(items.length), tone: 'neutral' },
        { label: 'Página', value: `${pag?.page ?? 1} de ${pag?.pages ?? 1}`, tone: 'neutral' },
        { label: 'Campos modificados', value: String(fieldsModified.length), tone: 'neutral' },
        { label: 'Usuarios', value: String(usersInvolved.length), tone: 'neutral' },
      ]);

      const metaRows: { label: string; value: string }[] = [
        { label: 'Propiedad', value: `#${pid}` },
        { label: 'Total de cambios', value: String(pag?.total ?? items.length) },
      ];
      if (fv.from) metaRows.push({ label: 'Desde', value: fv.from });
      if (fv.to) metaRows.push({ label: 'Hasta', value: fv.to });
      if (fv.field) metaRows.push({ label: 'Campo', value: this.fieldLabel(fv.field) });
      if (fv.user) metaRows.push({ label: 'Usuario', value: fv.user });

      const table = buildTable(
        [
          { label: 'Campo', align: 'left' },
          { label: 'Valor anterior', align: 'left' },
          { label: 'Valor nuevo', align: 'left' },
          { label: 'Usuario', align: 'left' },
          { label: 'Fecha', align: 'right' },
        ],
        items.map((c: ChangeRecordDto) => [
          this.fieldLabel(c.field),
          (c.old_value || '—').substring(0, 80),
          (c.new_value || '—').substring(0, 80),
          c.changed_by,
          new Date(c.changed_at).toLocaleString('es-MX', {
            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
          }),
        ])
      );

      const signatures = `
        <div style="display:flex; justify-content:space-between; margin-top: 16mm; padding-top: 10mm;">
          <div style="text-align:center; width: 45%;">
            <div style="border-top: 0.6pt solid #888; padding-top: 2mm;">Responsable de Auditoría</div>
          </div>
          <div style="text-align:center; width: 45%;">
            <div style="border-top: 0.6pt solid #888; padding-top: 2mm;">Director de Operaciones</div>
          </div>
        </div>`;

      const bodyHtml = grid + `<h2>Detalle de cambios</h2>` + table + signatures;
      const html = buildReportShell({
        title: 'Historial de Cambios — Propiedad',
        subtitle: `Propiedad #${pid}`,
        metaRows,
        bodyHtml,
      });

      await this.reports.exportPdf(html, `auditoria-propiedad-${pid}-${new Date().toISOString().slice(0, 10)}`);
    } catch (err: unknown) {
      console.error('[PropertyHistory] PDF export failed', toErrorMessage(err, 'unknown error'));
    } finally {
      this.exportingPdf.set(false);
    }
  }

  async exportXlsx(): Promise<void> {
    this.exportingXlsx.set(true);
    try {
      const pid = this.propId();
      const items = this.items();
      const pag = this.pagination();
      const fv = this.filterForm.getRawValue();
      const fieldsModified = [...new Set(items.map((i: ChangeRecordDto) => i.field))];
      const usersInvolved = [...new Set(items.map((i: ChangeRecordDto) => i.changed_by))];

      await this.reports.exportXlsx({
        filename: `auditoria-propiedad-${pid}-${new Date().toISOString().slice(0, 10)}`,
        sheet_title: `Auditoría · Propiedad #${pid}`,
        sheets: [
          {
            name: 'Resumen',
            headers: [{ label: 'Métrica' }, { label: 'Valor' }],
            rows: [
              ['ID propiedad', pid],
              ['Total de cambios', pag?.total ?? items.length],
              ['Registros en esta página', items.length],
              ['Página actual', `${pag?.page ?? 1} de ${pag?.pages ?? 1}`],
              ['Campos modificados', fieldsModified.length],
              ['Usuarios involucrados', usersInvolved.length],
              ['Filtro Desde', fv.from || '—'],
              ['Filtro Hasta', fv.to || '—'],
              ['Filtro Campo', fv.field ? this.fieldLabel(fv.field) : '—'],
              ['Filtro Usuario', fv.user || '—'],
            ],
            column_widths: { A: 32, B: 36 },
          },
          {
            name: 'Cambios',
            headers: [
              { label: 'Fecha' },
              { label: 'Campo' },
              { label: 'Valor anterior' },
              { label: 'Valor nuevo' },
              { label: 'Usuario' },
            ],
            rows: items.map((c: ChangeRecordDto) => [
              new Date(c.changed_at).toLocaleString('es-MX'),
              this.fieldLabel(c.field),
              c.old_value || '—',
              c.new_value || '—',
              c.changed_by,
            ]),
            column_widths: { A: 22, B: 24, C: 40, D: 40, E: 22 },
          },
        ],
      });
    } catch (err: unknown) {
      console.error('[PropertyHistory] XLSX export failed', toErrorMessage(err, 'unknown error'));
    } finally {
      this.exportingXlsx.set(false);
    }
  }

  readonly pages = computed(() => {
    const p = this.pagination();
    if (!p) return [];
    const total = p.pages;
    const current = p.page;
    const result: number[] = [];
    const start = Math.max(1, current - 2);
    const end = Math.min(total, current + 2);
    for (let i = start; i <= end; i++) result.push(i);
    return result;
  });

  readonly fieldLabel = (field: string) => {
    const labels: Record<string, string> = {
      hotel_name: 'Nombre oficial',
      display_name: 'Nombre comercial',
      description: 'Descripción',
      display_country_label: 'País / mercado',
    };
    return labels[field] || field.replace(/_/g, ' ');
  };
}
