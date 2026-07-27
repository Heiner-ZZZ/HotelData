import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { HttpClient, HttpParams } from '@angular/common/http';
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

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<AuditResponse | null>(null);
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

  constructor() {
    this.loadFilterOptions();
    this.route.queryParamMap
      .pipe(
        map(() => this.buildParams()),
        distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
        switchMap((params) => {
          this.viewState.set('loading');
          return this.fetchAuditLog(params);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (res) => {
          this.data.set(res);
          this.viewState.set(res.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
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

  private buildParams(): Record<string, string | number> {
    const qp = this.route.snapshot.queryParamMap;
    const params: Record<string, string | number> = {};
    const page = Number(qp.get('page') || '1');
    const entityType = qp.get('entity_type') || this.filterForm.value.entityType || '';
    const action = qp.get('action') || this.filterForm.value.action || '';
    const propId = Number(qp.get('prop_id') || this.filterForm.value.propId || '0');
    const fromDate = qp.get('from_date') || this.filterForm.value.fromDate || '';
    const toDate = qp.get('to_date') || this.filterForm.value.toDate || '';
    if (page > 1) params['page'] = page;
    if (entityType) params['entity_type'] = entityType;
    if (action) params['action'] = action;
    if (propId > 0) params['prop_id'] = propId;
    if (fromDate) params['from_date'] = fromDate;
    if (toDate) params['to_date'] = toDate;
    return params;
  }

  private fetchAuditLog(params: Record<string, string | number>) {
    let httpParams = new HttpParams();
    Object.entries(params).forEach(([key, value]) => {
      httpParams = httpParams.set(key, String(value));
    });
    return this.http.get<AuditResponse>(
      `${this.apiConfig.baseUrl}/management/audit-log`,
      { params: httpParams, withCredentials: true },
    );
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
      const entityTypes = [...new Set(d.items.map((i) => i.entity_type))];
      const actions = [...new Set(d.items.map((i) => i.action))];
      const users = [...new Set(d.items.map((i) => i.changed_by))];

      const grid = buildSummaryGrid([
        { label: 'Total de registros', value: String(d.total), tone: 'neutral' },
        { label: 'En esta página', value: String(d.items.length), tone: 'neutral' },
        { label: 'Página', value: `${d.page} de ${d.pages || 1}`, tone: 'neutral' },
        { label: 'Entidades únicas', value: String(entityTypes.length), tone: 'neutral' },
        { label: 'Acciones únicas', value: String(actions.length), tone: 'neutral' },
        { label: 'Usuarios', value: String(users.length), tone: 'neutral' },
      ]);

      const metaRows = [
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
        d.items.map((entry) => [
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
    } catch (err) {
      console.error('[Audit] PDF export failed', err);
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
      const entityTypes = [...new Set(d.items.map((i) => i.entity_type))];
      const actions = [...new Set(d.items.map((i) => i.action))];
      const users = [...new Set(d.items.map((i) => i.changed_by))];

      await this.reports.exportXlsx({
        filename: `auditoria-sistema-${new Date().toISOString().slice(0, 10)}`,
        sheet_title: 'Reporte de Auditoría — Sistema HotelData',
        sheets: [
          {
            name: 'Resumen',
            headers: [{ label: 'Métrica' }, { label: 'Valor' }],
            rows: [
              ['Total de registros', d.total] as any,
              ['Registros en página', d.items.length] as any,
              ['Página actual', `${d.page} de ${d.pages || 1}`] as any,
              ['Entidades únicas', entityTypes.length] as any,
              ['Acciones únicas', actions.length] as any,
              ['Usuarios únicos', users.length] as any,
              ['Filtro Entidad', fv.entityType ? this.getEntityLabel(fv.entityType) : '—'] as any,
              ['Filtro Acción', fv.action ? this.getActionLabel(fv.action) : '—'] as any,
              ['Filtro Propiedad', fv.propId ? `#${fv.propId}` : '—'] as any,
              ['Desde', fv.fromDate || '—'] as any,
              ['Hasta', fv.toDate || '—'] as any,
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
            rows: d.items.map((entry) => [
              new Date(entry.timestamp).toLocaleString('es-MX'),
              this.getEntityLabel(entry.entity_type),
              this.getActionLabel(entry.action),
              entry.entity_id,
              entry.summary || '',
              entry.changed_by,
              entry.prop_id,
            ]) as any[],
            column_widths: { A: 22, B: 24, C: 22, D: 22, E: 50, F: 22, G: 14 },
          },
        ],
      });
    } catch (err) {
      console.error('[Audit] XLSX export failed', err);
    } finally {
      this.exportingXlsx.set(false);
    }
  }

  getKeys(obj: Record<string, unknown> | null | undefined): string[] {
    if (!obj) return [];
    return Object.keys(obj);
  }
}
