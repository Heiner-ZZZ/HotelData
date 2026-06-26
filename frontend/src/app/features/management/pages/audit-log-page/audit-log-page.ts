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
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

import { HttpClient, HttpParams } from '@angular/common/http';
import { API_CONFIG } from '../../../../core/api/api.config';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
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
  };

  readonly actionLabel: Record<string, string> = {
    create: 'Creación',
    update: 'Actualización',
    delete: 'Eliminación',
    soft_delete: 'Borrado lógico',
    restore: 'Restauración',
    batch_update: 'Actualización masiva',
  };

  readonly actionIcon: Record<string, string> = {
    create: 'add_circle',
    update: 'edit',
    delete: 'delete',
    soft_delete: 'inventory_2',
    restore: 'restore',
    batch_update: 'batch_prediction',
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
        return 'var(--success)';
      case 'update':
      case 'batch_update':
        return 'var(--accent)';
      case 'delete':
      case 'soft_delete':
        return 'var(--danger)';
      case 'restore':
        return 'var(--warning)';
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

  async exportPdf(): Promise<void> {
    this.exportingPdf.set(true);
    try {
      const d = this.data();
      if (!d || !d.items.length) return;

      const now = new Date();
      const dateStr = now.toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' });
      const timeStr = now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });

      const doc = new jsPDF('p', 'mm', 'a4');
      const pageW = doc.internal.pageSize.getWidth();
      const margin = 18;
      const contentW = pageW - margin * 2;

      const addFooter = (pdf: jsPDF, pageNum: number, totalPages: number) => {
        const h = pdf.internal.pageSize.getHeight();
        pdf.setDrawColor(200, 200, 200);
        pdf.line(margin, h - 22, pageW - margin, h - 22);
        pdf.setFontSize(7);
        pdf.setTextColor(140, 140, 140);
        pdf.text('CONFIDENCIAL — Este documento contiene información sensible del sistema HotelData.', margin, h - 16);
        pdf.text(`Generado: ${dateStr} ${timeStr}`, margin, h - 12);
        pdf.text(`Página ${pageNum} de ${totalPages}`, pageW - margin, h - 12, { align: 'right' });
        pdf.text('HotelData — Sistema de Gestión Hotelera', margin, h - 8);
      };

      // ─── HEADER ───
      doc.setFillColor(25, 60, 120);
      doc.rect(0, 0, pageW, 38, 'F');
      doc.setFontSize(18);
      doc.setTextColor(255, 255, 255);
      doc.text('HotelData', margin, 16);
      doc.setFontSize(9);
      doc.setTextColor(200, 215, 240);
      doc.text('Sistema de Gestión Hotelera', margin, 22);
      doc.setFontSize(14);
      doc.setTextColor(255, 255, 255);
      doc.text('REPORTE DE AUDITORÍA', pageW - margin, 16, { align: 'right' });
      doc.setFontSize(8);
      doc.setTextColor(200, 215, 240);
      doc.text('Registro Centralizado de Acciones', pageW - margin, 22, { align: 'right' });

      doc.setFillColor(45, 120, 220);
      doc.rect(0, 38, pageW, 2, 'F');

      let y = 50;

      // ─── FILTERS INFO ───
      const fv = this.filterForm.getRawValue();
      const hasFilters = fv.entityType || fv.action || fv.propId || fv.fromDate || fv.toDate;
      if (hasFilters) {
        doc.setFillColor(245, 247, 250);
        doc.roundedRect(margin, y, contentW, hasFilters ? 16 : 14, 3, 3, 'F');
        doc.setFontSize(7);
        doc.setTextColor(100, 110, 130);
        doc.text('FILTROS APLICADOS', margin + 6, y + 5);
        y += 9;
        doc.setFontSize(8);
        doc.setTextColor(60, 60, 60);
        const filters: string[] = [];
        if (fv.entityType) filters.push(`Entidad: ${this.getEntityLabel(fv.entityType)}`);
        if (fv.action) filters.push(`Acción: ${this.getActionLabel(fv.action)}`);
        if (fv.propId) filters.push(`Propiedad: #${fv.propId}`);
        if (fv.fromDate) filters.push(`Desde: ${fv.fromDate}`);
        if (fv.toDate) filters.push(`Hasta: ${fv.toDate}`);
        doc.text(filters.join('  |  '), margin + 6, y);
        y += 10;
      }

      // ─── SUMMARY ───
      doc.setFontSize(7);
      doc.setTextColor(100, 110, 130);
      doc.text('RESUMEN', margin, y);
      y += 5;

      const entityTypes = [...new Set(d.items.map(i => i.entity_type))];
      const actions = [...new Set(d.items.map(i => i.action))];
      const users = [...new Set(d.items.map(i => i.changed_by))];
      const summaryItems: [string, string][] = [
        ['Total de registros', String(d.total)],
        ['Registros en página', String(d.items.length)],
        ['Página', `${d.page} de ${d.pages || 1}`],
        ['Entidades', entityTypes.map(t => this.getEntityLabel(t)).join(', ')],
        ['Acciones', actions.map(a => this.getActionLabel(a)).join(', ')],
        ['Usuarios', users.join(', ')],
      ];

      let sx = margin;
      let sy = y;
      const colW = contentW / 2;
      summaryItems.forEach((item, idx) => {
        if (idx > 0 && idx % 2 === 0) { sx = margin; sy += 10; }
        doc.setFontSize(7);
        doc.setTextColor(100, 110, 130);
        doc.text(item[0], sx, sy);
        doc.setFontSize(9);
        doc.setTextColor(30, 30, 30);
        doc.text(item[1], sx, sy + 4);
        sx += colW;
      });

      y = sy + 14;

      // ─── TABLE ───
      doc.setFontSize(7);
      doc.setTextColor(100, 110, 130);
      doc.text('DETALLE DE REGISTROS', margin, y);
      y += 3;

      const tableData = d.items.map(entry => [
        this.getEntityLabel(entry.entity_type),
        this.getActionLabel(entry.action),
        (entry.summary || '').substring(0, 80),
        entry.changed_by,
        new Date(entry.timestamp).toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
      ]);

      autoTable(doc, {
        startY: y,
        margin: { left: margin, right: margin },
        head: [['Entidad', 'Acción', 'Resumen', 'Usuario', 'Fecha']],
        body: tableData,
        styles: {
          fontSize: 7.5,
          cellPadding: 3,
          textColor: [40, 40, 40],
          lineColor: [220, 225, 235],
          lineWidth: 0.3,
        },
        headStyles: {
          fillColor: [25, 60, 120],
          textColor: [255, 255, 255],
          fontStyle: 'bold',
          fontSize: 7.5,
        },
        alternateRowStyles: {
          fillColor: [248, 249, 252],
        },
        columnStyles: {
          0: { cellWidth: 30 },
          1: { cellWidth: 28 },
          2: { cellWidth: 'auto' },
          3: { cellWidth: 28 },
          4: { cellWidth: 38, halign: 'right' },
        },
        didDrawPage: (data) => {
          addFooter(doc, data.pageNumber, doc.getNumberOfPages());
        },
      });

      // Signature section
      const afterTable = (doc as any).lastAutoTable?.finalY ?? y + 20;
      if (afterTable < 240) {
        let sigY = afterTable + 15;
        doc.setDrawColor(180, 180, 180);
        doc.setLineWidth(0.3);
        doc.line(margin, sigY, margin + 60, sigY);
        doc.line(pageW / 2 + 10, sigY, pageW / 2 + 70, sigY);
        sigY += 5;
        doc.setFontSize(7);
        doc.setTextColor(100, 110, 130);
        doc.text('Responsable de Auditoría', margin + 30, sigY, { align: 'center' });
        doc.text('Director de Operaciones', pageW / 2 + 40, sigY, { align: 'center' });
      }

      // Final footer on all pages
      const totalPages = doc.getNumberOfPages();
      for (let i = 1; i <= totalPages; i++) {
        doc.setPage(i);
        addFooter(doc, i, totalPages);
      }

      doc.save(`auditoria-sistema-${now.toISOString().slice(0, 10)}.pdf`);
    } catch {
      // Silently fail
    } finally {
      this.exportingPdf.set(false);
    }
  }

  getKeys(obj: Record<string, unknown> | null | undefined): string[] {
    if (!obj) return [];
    return Object.keys(obj);
  }
}
