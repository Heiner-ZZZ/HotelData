import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { Currency } from '../../models/currencies.model';
import type { CurrencyListDto } from '../../models/currencies.dto';
import { CurrenciesApiService } from '../../services/currencies-api.service';
import { mapCurrency } from '../../mappers/currencies.mapper';

@Component({
  selector: 'app-currencies-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    FormsModule,
    LoadingStateComponent,
    PageHeaderComponent,
  ],
  templateUrl: './currencies-page.html',
  styleUrl: './currencies-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CurrenciesPageComponent {
  private readonly api = inject(CurrenciesApiService);
  private readonly toast = inject(ToastService);

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

  // ── Add/Edit modal ──
  readonly showModal = signal(false);
  readonly editingCode = signal<string | null>(null);
  readonly form = signal({ code: '', name: '', symbol: '$', decimals: 2 });
  readonly saving = signal(false);

  // ── Delete confirmation ──
  readonly confirmDeleteCode = signal<string | null>(null);

  openAdd() {
    this.editingCode.set(null);
    this.form.set({ code: '', name: '', symbol: '$', decimals: 2 });
    this.showModal.set(true);
  }

  openEdit(cur: Currency) {
    this.editingCode.set(cur.code);
    this.form.set({ code: cur.code, name: cur.name, symbol: cur.symbol, decimals: cur.decimals });
    this.showModal.set(true);
  }

  closeModal() {
    this.showModal.set(false);
    this.editingCode.set(null);
  }

  save() {
    const f = this.form();
    if (!f.code || !f.name) return;
    this.saving.set(true);

    const req$ = this.editingCode()
      ? this.api.update(this.editingCode()!, { name: f.name, symbol: f.symbol, decimals: f.decimals })
      : this.api.create({ code: f.code.toUpperCase(), name: f.name, symbol: f.symbol, decimals: f.decimals });

    req$.subscribe({
      next: () => {
        this.saving.set(false);
        this.closeModal();
        this.currenciesResource.reload();
        this.toast.success(this.editingCode() ? 'Moneda actualizada' : 'Moneda creada');
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error(err?.error?.detail || 'Error al guardar la moneda');
      },
    });
  }

  toggle(cur: Currency) {
    this.api.toggle(cur.code).subscribe({
      next: () => {
        this.currenciesResource.reload();
        this.toast.success(`Moneda ${cur.active ? 'desactivada' : 'activada'}`);
      },
      error: (err) => {
        this.toast.error(err?.error?.detail || 'Error al cambiar estado');
      },
    });
  }

  requestDelete(code: string) {
    this.confirmDeleteCode.set(code);
  }

  cancelDelete() {
    this.confirmDeleteCode.set(null);
  }

  confirmDelete(code: string) {
    this.confirmDeleteCode.set(null);
    this.api.delete(code).subscribe({
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
