import { DatePipe } from '@angular/common';
import { HttpClient, HttpParams, HttpErrorResponse, HttpResourceRequest, httpResource } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { API_CONFIG } from '../../../../core/api/api.config';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ReportsExportService } from '../../../../shared/services/reports-export.service';
import {
  buildReportShell,
  buildSummaryGrid,
  buildTable,
} from '../../../../shared/utils/report-html-templates';
import type { ViewState } from '../../../../shared/types/ui-state.type';

interface AuditEntry {
  timestamp: string;
  prop_id: number;
  entity_type: string;
  entity_id: string;
  action: string;
  summary: string;
  changed_by: string;
  diff?: Record<string, { old: unknown; new: unknown }>;
  metadata?: Record<string, unknown>;
}

interface AuditResponse {
  items: AuditEntry[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface FilterOptions {
  entity_types: string[];
  actions: string[];
}

/** Helper: extract a runtime error message without relying on `any`.
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
  selector: 'app-audit-log-page',
  imports: [
    DatePipe,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    ReactiveFormsModule,
    RouterLink,
  ],
  templateUrl: './audit-log-page.html',
  styleUrl: './audit-log-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuditLogPageComponent {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  private readonly reports = inject(ReportsExportService);

  /** Reactive query-params bridge — toSignal keeps URL the source of truth. */
  private readonly qp = toSignal(this.route.queryParamMap, {
    initialValue: this.route.snapshot.queryParamMap,
  });

  readonly viewState = computed<ViewState>(() => {
    const v = this.auditResource.value();
    if (this.auditResource.isLoading() && !v) return 'loading';
    const err = this.auditResource.error();
    if (err instanceof HttpErrorResponse && err.status === 404) return 'empty';
    if (err) return 'error';
    return v?.items.length ? 'success' : 'empty';
  });

  /** Snapshot of filter UI state for the URL write-back. */
  readonly data = computed(() => this.auditResource.value() ?? null);
  readonly filterOptions = signal<FilterOptions>({ entity_types: [], actions: [] });
  readonly selectedEntry = signal<AuditEntry | null>(null);
  readonly showDetail = signal(false);

  readonly filterForm = this.fb.nonNullable.group({
    entityType: [''],
    action: [''],
    propId: [0],
    fromDate: [''],
    toDate: [''],
  });

  readonly entityTypeLabel: Record<string, string> = {
    room_type: 'Tipos de habitación',
    inventory_entry: 'Inventario',
    rate_plan: 'Planes tarifarios',
    rate_calendar: 'Calendario de tarifas',
    policy: 'Políticas',
    amenity: 'Amenidades',
    content: 'Contenido',
    reservation: 'Reservas / Recepción',
    housekeeping_task: 'Limpieza',
  };

  readonly actionLabel: Record<string, string> = {
    create: 'Creación',
    update: 'Actualización',
    delete: 'Eliminación',
    soft_delete: 'Borrado lógico',
    restore: 'Restauración',
    batch_update: 'Actualización masiva',
    confirm: 'Confirmar reserva',
    reject: 'Rechazar reserva',
    cancel: 'Cancelar reserva',
    check_in: 'Check-in',
    check_out: 'Check-out',
    reassign_room: 'Reasignar hab.',
    document_change: 'Cambio auto.',
  };

  readonly actionIcon: Record<string, string> = {
    create: 'add_circle',
    update: 'edit',
    delete: 'delete',
    soft_delete: 'inventory_2',
    restore: 'restore',
    batch_update: 'batch_prediction',
    confirm: 'check_circle',
    reject: 'cancel',
    cancel: 'event_busy',
    check_in: 'login',
    check_out: 'logout',
    reassign_room: 'swap_horiz',
    document_change: 'description',
    read: 'visibility',
    access_denied: 'block',
    restock: 'inventory_2',
    open: 'door_open',
  };

  /** Reactive httpResource — re-fetches whenever qp() changes. */
  readonly auditResource = httpResource<AuditResponse>(() => {
    const q = this.qp();
    const requestedPage = Number(q.get('page') ?? '1');
    const page = Number.isInteger(requestedPage) && requestedPage >= 1 ? requestedPage : 1;
    const entityType = q.get('entity_type') || this.filterForm.value.entityType || '';
    const action = q.get('action') || this.filterForm.value.action || '';
    const requestedPropId = Number(q.get('prop_id') || this.filterForm.value.propId || '0');
    const propId = Number.isInteger(requestedPropId) && requestedPropId >= 1 ? requestedPropId : 0;
    const fromDate = q.get('from_date') || this.filterForm.value.fromDate || '';
    const toDate = q.get('to_date') || this.filterForm.value.toDate || '';
    // Optional filters must be omitted when unset. In particular, `prop_id=0`
    // violates the backend contract (`prop_id` is optional, but when present
    // it must be >= 1) and causes a 422 on the initial request.
    let params = new HttpParams().set('page', String(page));
    if (entityType) params = params.set('entity_type', entityType);
    if (action) params = params.set('action', action);
    if (propId > 0) params = params.set('prop_id', String(propId));
    if (fromDate) params = params.set('from_date', fromDate);
    if (toDate) params = params.set('to_date', toDate);
    const request: HttpResourceRequest = {
      url: `${this.apiConfig.baseUrl}/management/audit-log`,
      method: 'GET',
      params,
      withCredentials: true,
    };
    return request;
  });

  constructor() {
    this.loadFilterOptions();
  }

  private loadFilterOptions(): void {
    this.http
      .get<FilterOptions>(`${this.apiConfig.baseUrl}/management/audit-log/entity-types`, {
        withCredentials: true,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (opts) => this.filterOptions.set(opts),
        // Silently fail — filters just won't show dropdowns
      });
  }

  /** Navigate via Angular Router — this triggers the route.queryParamMap subscription
   *  that already exists in the constructor, making filters truly reactive. */
  private navigateWithFilters(extraParams?: Record<string, string | number | null>): void {
    const fv = this.filterForm.getRawValue();
    const qp: Record<string, string | number | null> = {
      entity_type: fv.entityType || null,
      action: fv.action || null,
      prop_id: (fv.propId && fv.propId > 0) ? fv.propId : null,
      from_date: fv.fromDate || null,
      to_date: fv.toDate || null,
      page: null,
      ...extraParams,
    };
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: qp,
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  applyFilters(): void {
    this.navigateWithFilters();
  }

  clearFilters(): void {
    this.filterForm.reset();
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {},
      queryParamsHandling: '',
      replaceUrl: true,
    });
  }

  goToPage(page: number): void {
    this.navigateWithFilters({ page: page > 1 ? page : null });
  }

  openDetail(entry: AuditEntry): void {
    this.selectedEntry.set(entry);
    this.showDetail.set(true);
  }

  closeDetail(): void {
    this.showDetail.set(false);
    this.selectedEntry.set(null);
  }

  getEntityLabel(type: string): string {
    return this.entityTypeLabel[type] || type.replace(/_/g, ' ');
  }

  getActionLabel(action: string): string {
    return this.actionLabel[action] || action.replace(/_/g, ' ');
  }

  getActionIcon(action: string): string {
    return this.actionIcon[action] || 'info';
  }

  getActionColor(action: string): string {
    switch (action) {
      case 'create':
      case 'confirm':
        return 'var(--success)';
      case 'update':
      case 'batch_update':
      case 'check_in':
      case 'check_out':
        return 'var(--accent)';
      case 'delete':
      case 'soft_delete':
      case 'reject':
      case 'cancel':
        return 'var(--danger)';
      case 'restore':
      case 'reassign_room':
      case 'open':
        return 'var(--warning)';
      case 'restock':
        return 'var(--success)';
      case 'read':
        return 'var(--muted-text)';
      case 'access_denied':
        return 'var(--danger)';
      default:
        return 'var(--muted-text)';
    }
  }

  readonly pages = computed(() => {
    const d = this.data();
    if (!d) return [];
    const total = d.pages;
    const current = d.page;
    const result: number[] = [];
    const start = Math.max(1, current - 2);
    const end = Math.min(total, current + 2);
    for (let i = start; i <= end; i++) result.push(i);
    return result;
  });

  readonly stats = computed(() => {
    const d = this.data();
    if (!d) return null;
    return {
      total: d.total,
      page: d.page,
      pages: d.pages || 1,
      perPage: d.per_page,
    };
  });

  readonly exportingPdf = signal(false);
  readonly exportingXlsx = signal(false);

  async exportPdf(): Promise<void> {
    this.exportingPdf.set(true);
    try {
      const d = this.data();
      if (!d || !d.items.length) return;
      const fv = this.filterForm.getRawValue();
      const entityTypes = [...new Set(d.items.map((i: AuditEntry) => i.entity_type))];
      const actions = [...new Set(d.items.map((i: AuditEntry) => i.action))];
      const users = [...new Set(d.items.map((i: AuditEntry) => i.changed_by))];

      const grid = buildSummaryGrid([
        { label: 'Total de registros', value: String(d.total), tone: 'neutral' },
        { label: 'En esta página', value: String(d.items.length), tone: 'neutral' },
        { label: 'Página', value: `${d.page} de ${d.pages || 1}`, tone: 'neutral' },
        { label: 'Entidades únicas', value: String(entityTypes.length), tone: 'neutral' },
        { label: 'Acciones únicas', value: String(actions.length), tone: 'neutral' },
        { label: 'Usuarios', value: String(users.length), tone: 'neutral' },
      ]);

      const metaRows: { label: string; value: string }[] = [
        { label: 'Total', value: String(d.total) },
        { label: 'Página', value: `${d.page} de ${d.pages || 1}` },
      ];
      if (fv.entityType) metaRows.push({ label: 'Entidad', value: this.getEntityLabel(fv.entityType) });
      if (fv.action) metaRows.push({ label: 'Acción', value: this.getActionLabel(fv.action) });
      if (fv.propId) metaRows.push({ label: 'Propiedad', value: `#${fv.propId}` });
      if (fv.fromDate) metaRows.push({ label: 'Desde', value: fv.fromDate });
      if (fv.toDate) metaRows.push({ label: 'Hasta', value: fv.toDate });

      const table = buildTable(
        [
          { label: 'Entidad', align: 'left' },
          { label: 'Acción', align: 'left' },
          { label: 'Resumen', align: 'left' },
          { label: 'Usuario', align: 'left' },
          { label: 'Fecha', align: 'right' },
        ],
        d.items.map((entry: AuditEntry) => [
          this.getEntityLabel(entry.entity_type),
          this.getActionLabel(entry.action),
          (entry.summary || '').substring(0, 100),
          entry.changed_by,
          new Date(entry.timestamp).toLocaleString('es-MX', {
            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
          }),
        ])
      );

      const signatureHtml = `
        <div style="display:flex; justify-content:space-between; margin-top: 16mm; padding-top: 10mm;">
          <div style="text-align:center; width: 45%;">
            <div style="border-top: 0.6pt solid #888; padding-top: 2mm;">Responsable de Auditoría</div>
          </div>
          <div style="text-align:center; width: 45%;">
            <div style="border-top: 0.6pt solid #888; padding-top: 2mm;">Director de Operaciones</div>
          </div>
        </div>`;

      const bodyHtml = grid + `<h2>Detalle de registros</h2>` + table + signatureHtml;
      const html = buildReportShell({
        title: 'Reporte de Auditoría',
        subtitle: 'Registro Centralizado de Acciones',
        metaRows,
        bodyHtml,
      });

      await this.reports.exportPdf(html, `auditoria-sistema-${new Date().toISOString().slice(0, 10)}`);
    } catch (err: unknown) {
      console.error('[Audit] PDF export failed', toErrorMessage(err, 'unknown error'));
    } finally {
      this.exportingPdf.set(false);
    }
  }

  async exportXlsx(): Promise<void> {
    this.exportingXlsx.set(true);
    try {
      const d = this.data();
      if (!d || !d.items.length) return;
      const fv = this.filterForm.getRawValue();
      const entityTypes = [...new Set(d.items.map((i: AuditEntry) => i.entity_type))];
      const actions = [...new Set(d.items.map((i: AuditEntry) => i.action))];
      const users = [...new Set(d.items.map((i: AuditEntry) => i.changed_by))];

      await this.reports.exportXlsx({
        filename: `auditoria-sistema-${new Date().toISOString().slice(0, 10)}`,
        sheet_title: 'Reporte de Auditoría — Sistema HotelData',
        sheets: [
          {
            name: 'Resumen',
            headers: [{ label: 'Métrica' }, { label: 'Valor' }],
            rows: [
              ['Total de registros', d.total],
              ['Registros en página', d.items.length],
              ['Página actual', `${d.page} de ${d.pages || 1}`],
              ['Entidades únicas', entityTypes.length],
              ['Acciones únicas', actions.length],
              ['Usuarios únicos', users.length],
              ['Filtro Entidad', fv.entityType ? this.getEntityLabel(fv.entityType) : '—'],
              ['Filtro Acción', fv.action ? this.getActionLabel(fv.action) : '—'],
              ['Filtro Propiedad', fv.propId ? `#${fv.propId}` : '—'],
              ['Desde', fv.fromDate || '—'],
              ['Hasta', fv.toDate || '—'],
            ],
            column_widths: { A: 32, B: 36 },
          },
          {
            name: 'Registros',
            headers: [
              { label: 'Fecha' },
              { label: 'Entidad' },
              { label: 'Acción' },
              { label: 'Entidad ID' },
              { label: 'Resumen' },
              { label: 'Usuario' },
              { label: 'Propiedad' },
            ],
            rows: d.items.map((entry: AuditEntry) => [
              new Date(entry.timestamp).toLocaleString('es-MX'),
              this.getEntityLabel(entry.entity_type),
              this.getActionLabel(entry.action),
              entry.entity_id,
              entry.summary || '',
              entry.changed_by,
              entry.prop_id,
            ]),
            column_widths: { A: 22, B: 24, C: 22, D: 22, E: 50, F: 22, G: 14 },
          },
        ],
      });
    } catch (err: unknown) {
      console.error('[Audit] XLSX export failed', toErrorMessage(err, 'unknown error'));
    } finally {
      this.exportingXlsx.set(false);
    }
  }

  getKeys(obj: Record<string, unknown> | null | undefined): string[] {
    if (!obj) return [];
    return Object.keys(obj);
  }
}
