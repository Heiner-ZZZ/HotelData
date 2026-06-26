import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { filter, map, switchMap } from 'rxjs';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

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
    const el = document.querySelector('.history-export-area');
    if (!el) {
      this.exportingPdf.set(false);
      return;
    }
    try {
      const canvas = await html2canvas(el as HTMLElement, {
        scale: 2,
        backgroundColor: '#ffffff',
        logging: false,
      });
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('l', 'mm', 'a4');
      const pdfW = pdf.internal.pageSize.getWidth();
      const pdfH = (canvas.height * pdfW) / canvas.width;
      let heightLeft = pdfH;
      let position = 0;
      const pageH = pdf.internal.pageSize.getHeight();

      pdf.addImage(imgData, 'PNG', 0, position, pdfW, pdfH);
      heightLeft -= pageH;

      while (heightLeft > 0) {
        position = heightLeft - pdfH;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, pdfW, pdfH);
        heightLeft -= pageH;
      }

      pdf.save(`historial-propiedad-${this.propId()}.pdf`);
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
