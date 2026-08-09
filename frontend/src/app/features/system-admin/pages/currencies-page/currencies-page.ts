import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { ConfirmDialogComponent } from '../../../../shared/ui/confirm-dialog/confirm-dialog.component';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { Currency } from '../../models/currencies.model';
import type { CurrencyListDto } from '../../models/currencies.dto';
import { CurrenciesApiService } from '../../services/currencies-api.service';
import { mapCurrency } from '../../mappers/currencies.mapper';

export type CurrencyStatusFilter = 'all' | 'active' | 'inactive';

/**
 * Catálogo de monedas (fuente de verdad: colección `system_currencies`).
 *
 * Diseño informado por los patrones de referencia de Stripe (tabla de códigos
 * ISO con anotación de monedas de cero decimales) y Wise (catálogo navegable),
 * alineado con las páginas de catálogo del propio sistema (stats-grid +
 * table-card de system-users).
 *
 * El nav-chip de modo (`app-operation-mode-indicator`) se sincroniza con cada
 * interacción: insert (crear), update (editar/activar), delete (confirmar
 * borrado). Es la misma mecánica transient del resto de módulos (rooms,
 * amenities, maintenance…).
 */
@Component({
  selector: 'app-currencies-page',
  imports: [
    ConfirmDialogComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    FormsModule,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './currencies-page.html',
  styleUrl: './currencies-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CurrenciesPageComponent {
  private readonly api = inject(CurrenciesApiService);
  private readonly toast = inject(ToastService);
  private readonly opMode = inject(OperationModeService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly destroyRef = inject(DestroyRef);

  readonly currenciesResource = httpResource<Currency[]>(
    () => '/api/management/currencies',
    {
      parse: (dto) => (dto as CurrencyListDto).currencies.map(mapCurrency),
    }
  );

  readonly viewState = computed<ViewState>(() => {
    if (this.currenciesResource.isLoading()) return 'loading';
    if (this.currenciesResource.error()) return 'error';
    const list = this.currenciesResource.value();
    return list?.length ? 'success' : 'empty';
  });

  // ── Resumen (stats cards) ─────────────────────────────────────────────

  readonly stats = computed(() => {
    const list = this.currenciesResource.value() ?? [];
    return {
      total: list.length,
      active: list.filter((c) => c.active).length,
      zeroDecimal: list.filter((c) => c.decimals === 0).length,
    };
  });

  // ── Búsqueda y filtros ────────────────────────────────────────────────

  readonly search = signal('');
  readonly statusFilter = signal<CurrencyStatusFilter>('all');

  /** Opciones del filtro segmentado Todas / Activas / Inactivas. */
  readonly statusOptions: readonly (readonly [CurrencyStatusFilter, string])[] = [
    ['all', 'Todas'],
    ['active', 'Activas'],
    ['inactive', 'Inactivas'],
  ];

  readonly filteredCurrencies = computed(() => {
    const q = this.search().trim().toLowerCase();
    const status = this.statusFilter();
    return (this.currenciesResource.value() ?? []).filter((cur) => {
      if (status === 'active' && !cur.active) return false;
      if (status === 'inactive' && cur.active) return false;
      if (q && !(cur.code.toLowerCase().includes(q) || cur.name.toLowerCase().includes(q))) return false;
      return true;
    });
  });

  /**
   * Preview determinista de cómo se vería un importe en esta moneda:
   * `$1.234,50` (decimals=2) o `¥1.235` (decimals=0, redondeado).
   * Es la firma visual de la página: cada fila demuestra el formato real
   * que verán los hoteles en pricing/facturación (misma regla de
   * `decimals` de system_currencies que usa el registro de propiedades).
   */
  formatPreview(cur: { symbol: string; decimals: number }): string {
    const amount = 1234.5.toFixed(cur.decimals);
    const [int, dec] = amount.split('.');
    const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return dec ? `${cur.symbol}${grouped},${dec}` : `${cur.symbol}${grouped}`;
  }

  /** Una moneda es de "cero decimales" (CLP, COP, JPY…) — anotación estilo Stripe. */
  isZeroDecimal(cur: { decimals: number }): boolean {
    return cur.decimals === 0;
  }

  // ── Add/Edit modal ──
  readonly showModal = signal(false);
  readonly editingCode = signal<string | null>(null);
  readonly form = signal({ code: '', name: '', symbol: '$', decimals: 2 });
  readonly saving = signal(false);

  constructor() {
    // Si la página se destruye con el modal abierto, no dejar el chip pegado
    // en un modo de escritura (misma guarda que amenities/maintenance).
    this.destroyRef.onDestroy(() => this.opMode.reset());
  }

  openAdd() {
    this.editingCode.set(null);
    this.form.set({ code: '', name: '', symbol: '$', decimals: 2 });
    this.showModal.set(true);
    this.opMode.setMode('insert', 'Nueva moneda');
  }

  openEdit(cur: Currency) {
    this.editingCode.set(cur.code);
    this.form.set({ code: cur.code, name: cur.name, symbol: cur.symbol, decimals: cur.decimals });
    this.showModal.set(true);
    this.opMode.setMode('update', cur.code);
  }

  closeModal() {
    this.showModal.set(false);
    this.editingCode.set(null);
    this.opMode.reset();
  }

  save() {
    const f = this.form();
    if (!f.code || !f.name) return;
    // Capturar antes de closeModal(): éste nullea editingCode y el mensaje
    // del toast dependería del valor ya reseteado.
    const isEdit = !!this.editingCode();
    this.saving.set(true);

    const req$ = isEdit
      ? this.api.update(this.editingCode()!, { name: f.name, symbol: f.symbol, decimals: f.decimals })
      : this.api.create({ code: f.code.toUpperCase(), name: f.name, symbol: f.symbol, decimals: f.decimals });

    req$.subscribe({
      next: () => {
        this.saving.set(false);
        this.closeModal();
        this.currenciesResource.reload();
        this.toast.success(isEdit ? 'Moneda actualizada' : 'Moneda creada');
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error(err?.error?.detail || 'Error al guardar la moneda');
      },
    });
  }

  /**
   * Activar/desactivar. Mientras la petición está en vuelo el chip muestra
   * "Editando {code}" (update); al terminar (éxito o error) vuelve a lectura.
   */
  toggle(cur: Currency) {
    const release = this.opMode.setMode('update', cur.code);
    this.api.toggle(cur.code).subscribe({
      next: () => {
        release();
        this.currenciesResource.reload();
        this.toast.success(`Moneda ${cur.active ? 'desactivada' : 'activada'}`);
      },
      error: (err) => {
        release();
        this.toast.error(err?.error?.detail || 'Error al cambiar estado');
      },
    });
  }

  /**
   * Flujo de borrado con el ConfirmDialogService compartido: mientras el
   * diálogo está abierto el chip muestra "Eliminando {code}" (delete) y se
   * restaura solo al cerrar (confirmar o cancelar).
   */
  async requestDelete(cur: Currency): Promise<void> {
    const ok = await this.confirmDialog.open({
      title: 'Eliminar moneda',
      message: `¿Eliminar la moneda ${cur.code} (${cur.name})?`,
      details: [
        'Esta acción no se puede deshacer.',
        'Si alguna propiedad usa esta moneda, el sistema rechazará el borrado: desactívala en su lugar.',
      ],
      confirmLabel: 'Eliminar',
      cancelLabel: 'Cancelar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: cur.code,
    });
    if (!ok) return;

    this.api.delete(cur.code).subscribe({
      next: () => {
        this.currenciesResource.reload();
        this.toast.success('Moneda eliminada');
      },
      error: (err) => {
        this.toast.error(err?.error?.detail || 'Error al eliminar');
      },
    });
  }
}
