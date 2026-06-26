import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { filter, map, switchMap } from 'rxjs';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ChangeRecordDto, PropertyHistoryResponseDto } from '../../models/properties.dto';
import { PropertiesApiService } from '../../services/properties-api.service';

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
      const now = new Date();
      const dateStr = now.toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' });
      const timeStr = now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });

      const doc = new jsPDF('p', 'mm', 'a4');
      const pageW = doc.internal.pageSize.getWidth();
      const margin = 18;
      const contentW = pageW - margin * 2;
      let y = 0;

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
      doc.text('INFORME DE AUDITORÍA', pageW - margin, 16, { align: 'right' });
      doc.setFontSize(8);
      doc.setTextColor(200, 215, 240);
      doc.text('Historial de Cambios — Propiedad', pageW - margin, 22, { align: 'right' });

      // Accent line
      doc.setFillColor(45, 120, 220);
      doc.rect(0, 38, pageW, 2, 'F');

      y = 50;

      // ─── PROPERTY INFO ───
      doc.setFillColor(245, 247, 250);
      doc.roundedRect(margin, y, contentW, 20, 3, 3, 'F');
      doc.setFontSize(8);
      doc.setTextColor(100, 110, 130);
      doc.text('PROPIEDAD', margin + 6, y + 6);
      doc.text('ID', margin + 6, y + 13);
      doc.setFontSize(10);
      doc.setTextColor(30, 30, 30);
      doc.text(String(pid), margin + 30, y + 13);
      doc.setFontSize(8);
      doc.setTextColor(100, 110, 130);
      doc.text('FECHA DE GENERACIÓN', pageW / 2 + 10, y + 6);
      doc.setFontSize(10);
      doc.setTextColor(30, 30, 30);
      doc.text(`${dateStr} ${timeStr}`, pageW / 2 + 10, y + 13);

      y += 28;

      // ─── FILTERS APPLIED ───
      const hasFilters = fv.from || fv.to || fv.field || fv.user;
      if (hasFilters) {
        doc.setFontSize(7);
        doc.setTextColor(100, 110, 130);
        doc.text('FILTROS APLICADOS:', margin, y);
        y += 5;
        doc.setFontSize(8);
        doc.setTextColor(60, 60, 60);
        const filters: string[] = [];
        if (fv.from) filters.push(`Desde: ${fv.from}`);
        if (fv.to) filters.push(`Hasta: ${fv.to}`);
        if (fv.field) filters.push(`Campo: ${this.fieldLabel(fv.field)}`);
        if (fv.user) filters.push(`Usuario: ${fv.user}`);
        doc.text(filters.join('  |  '), margin, y);
        y += 8;
      }

      // ─── SUMMARY ───
      doc.setFontSize(7);
      doc.setTextColor(100, 110, 130);
      doc.text('RESUMEN', margin, y);
      y += 5;

      const summaryItems: [string, string][] = [
        ['Total de cambios', String(pag?.total ?? items.length)],
        ['Registros en esta página', String(items.length)],
        ['Página', `${pag?.page ?? 1} de ${pag?.pages ?? 1}`],
      ];

      const fieldsModified = [...new Set(items.map(i => i.field))];
      if (fieldsModified.length) {
        summaryItems.push(['Campos modificados', fieldsModified.map(f => this.fieldLabel(f)).join(', ')]);
      }
      const usersInvolved = [...new Set(items.map(i => i.changed_by))];
      if (usersInvolved.length) {
        summaryItems.push(['Usuarios involucrados', usersInvolved.join(', ')]);
      }

      const colW = contentW / 3;
      let sx = margin;
      let sy = y;
      summaryItems.forEach((item, idx) => {
        if (idx > 0 && idx % 3 === 0) { sx = margin; sy += 10; }
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
      doc.text('DETALLE DE CAMBIOS', margin, y);
      y += 3;

      const tableData = items.map(c => [
        this.fieldLabel(c.field),
        (c.old_value || '—').substring(0, 60),
        (c.new_value || '—').substring(0, 60),
        c.changed_by,
        new Date(c.changed_at).toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
      ]);

      autoTable(doc, {
        startY: y,
        margin: { left: margin, right: margin },
        head: [['Campo', 'Valor anterior', 'Valor nuevo', 'Usuario', 'Fecha']],
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
          0: { cellWidth: 32, fontStyle: 'bold' },
          1: { cellWidth: 'auto', textColor: [180, 50, 50] },
          2: { cellWidth: 'auto', textColor: [22, 130, 60] },
          3: { cellWidth: 28 },
          4: { cellWidth: 38, halign: 'right' },
        },
        didDrawPage: (data) => {
          addFooter(doc, data.pageNumber, doc.getNumberOfPages());
        },
      });

      // ─── SIGNATURE SECTION ───
      const afterTable = (doc as any).lastAutoTable?.finalY ?? y + 20;
      if (afterTable < 240) {
        let sigY = afterTable + 15;
        doc.setDrawColor(180, 180, 180);
        doc.setLineWidth(0.3);

        const sigLeft = margin;
        const sigRight = pageW / 2 + 10;
        const sigWidth = 60;

        doc.line(sigLeft, sigY, sigLeft + sigWidth, sigY);
        doc.line(sigRight, sigY, sigRight + sigWidth, sigY);

        sigY += 5;
        doc.setFontSize(7);
        doc.setTextColor(100, 110, 130);
        doc.text('Responsable de Auditoría', sigLeft + sigWidth / 2, sigY, { align: 'center' });
        doc.text('Director de Operaciones', sigRight + sigWidth / 2, sigY, { align: 'center' });
      }

      // Final footer on last page
      const totalPages = doc.getNumberOfPages();
      for (let i = 1; i <= totalPages; i++) {
        doc.setPage(i);
        addFooter(doc, i, totalPages);
      }

      doc.save(`auditoria-propiedad-${pid}-${now.toISOString().slice(0, 10)}.pdf`);
    } catch {
      // Silently fail
    } finally {
      this.exportingPdf.set(false);
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
