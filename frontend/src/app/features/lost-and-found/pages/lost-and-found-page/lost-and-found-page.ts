import { CurrencyPipe, DatePipe, SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subject, debounceTime, distinctUntilChanged, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { LostItemCreateDto, LostItemResponseDto, PaginatedResponse } from '../../models/lost-and-found.dto';
import { LostAndFoundApiService } from '../../services/lost-and-found-api.service';

@Component({
  selector: 'app-lost-and-found-page',
  imports: [CurrencyPipe, DatePipe, SlicePipe, FormsModule, EmptyStateComponent, ErrorStateComponent,
    LoadingStateComponent, PageHeaderComponent, RouterLink, StatusBadgeComponent],
  templateUrl: './lost-and-found-page.html',
  styleUrl: './lost-and-found-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LostAndFoundPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly api = inject(LostAndFoundApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<PaginatedResponse<LostItemResponseDto> | null>(null);
  readonly items = computed(() => this.data()?.items ?? []);
  readonly total = computed(() => this.data()?.total ?? 0);
  readonly currentPage = signal(1);
  readonly statusFilter = signal('');
  readonly searchQuery = signal('');
  readonly errorMessage = signal('');

  readonly search$ = new Subject<string>();

  // Modal state
  readonly showCreateModal = signal(false);
  readonly showDetailModal = signal(false);
  readonly selectedItem = signal<LostItemResponseDto | null>(null);
  readonly saving = signal(false);
  readonly modalError = signal('');

  // Create form
  readonly form = signal<LostItemCreateDto>({
    prop_id: 0,
    booking_id: '',
    guest_name: '',
    guest_contact: '',
    item_name: '',
    description: '',
    found_location: '',
    found_by: '',
    notes: '',
  });

  // Status badge config
  readonly statusColor: Record<string, string> = {
    pending: 'var(--color-warning)',
    claimed: 'var(--color-info)',
    returned: 'var(--color-success)',
    disposed: 'var(--color-danger)',
  };

  readonly statusLabel: Record<string, string> = {
    pending: 'Pendiente',
    claimed: 'Reclamado',
    returned: 'Devuelto',
    disposed: 'Desechado',
  };

  constructor() {
    // Pre-fill hotel from query param
    const prefilledPropId = Number(this.activatedRoute.snapshot.queryParamMap.get('prop_id') ?? '0');
    if (prefilledPropId) {
      this.form.update(f => ({ ...f, prop_id: prefilledPropId }));
    }

    this._loadList();

    // Debounced search
    this.search$
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe((query) => {
        this.searchQuery.set(query);
        this.currentPage.set(1);
        this._loadList();
      });
  }

  private _loadList() {
    this.viewState.set('loading');
    this.api.listItems({
      propId: this.form().prop_id || undefined,
      status: this.statusFilter() || undefined,
      search: this.searchQuery() || undefined,
      page: this.currentPage(),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.data.set(result);
        this.viewState.set('success');
      },
      error: () => {
        this.viewState.set('error');
        this.errorMessage.set('No se pudo cargar el listado de objetos perdidos.');
      },
    });
  }

  setPage(page: number) {
    this.currentPage.set(page);
    this._loadList();
  }

  setStatusFilter(status: string) {
    this.statusFilter.set(status);
    this.currentPage.set(1);
    this._loadList();
  }

  onSearch(value: string) {
    this.search$.next(value);
  }

  openCreateModal() {
    this.form.set({
      prop_id: this.form().prop_id || 0,
      booking_id: '',
      guest_name: '',
      guest_contact: '',
      item_name: '',
      description: '',
      found_location: '',
      found_by: '',
      notes: '',
    });
    this.modalError.set('');
    this.showCreateModal.set(true);
  }

  closeCreateModal() {
    this.showCreateModal.set(false);
  }

  createItem() {
    const f = this.form();
    if (!f.item_name.trim()) {
      this.modalError.set('El nombre del objeto es obligatorio.');
      return;
    }
    if (!f.prop_id) {
      this.modalError.set('Selecciona un hotel (prop_id).');
      return;
    }

    this.saving.set(true);
    this.modalError.set('');
    this.api.createItem(f).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.saving.set(false);
        this.showCreateModal.set(false);
        this._loadList();
      },
      error: (err: ApiError) => {
        this.saving.set(false);
        this.modalError.set(err.message || 'Error al crear el registro.');
      },
    });
  }

  openDetail(item: LostItemResponseDto) {
    this.selectedItem.set(item);
    this.showDetailModal.set(true);
  }

  closeDetail() {
    this.showDetailModal.set(false);
    this.selectedItem.set(null);
  }

  claimItem(item: LostItemResponseDto) {
    const returnedTo = prompt('¿Quién recibe el objeto? (nombre del huésped o staff)');
    if (returnedTo === null) return; // cancelled

    this.api.claimItem(item.id, returnedTo).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.closeDetail();
        this._loadList();
      },
      error: () => {
        this.modalError.set('Error al marcar como devuelto.');
      },
    });
  }

  disposeItem(item: LostItemResponseDto) {
    if (!confirm(`¿Estás seguro de marcar "${item.item_name}" como desechado? Esta acción no se puede deshacer.`)) return;

    this.api.disposeItem(item.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.closeDetail();
        this._loadList();
      },
      error: () => {
        this.modalError.set('Error al marcar como desechado.');
      },
    });
  }

  deleteItem(item: LostItemResponseDto) {
    if (!confirm(`¿Eliminar permanentemente "${item.item_name}"?`)) return;

    this.api.deleteItem(item.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.closeDetail();
        this._loadList();
      },
      error: () => {
        this.modalError.set('Error al eliminar.');
      },
    });
  }
}
