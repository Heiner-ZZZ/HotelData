import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { GuestsApiService, type GuestItem, type GuestsResponse } from '../../services/guests-api.service';

@Component({
  selector: 'app-guests-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
  ],
  templateUrl: './guests-page.html',
  styleUrl: './guests-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GuestsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(GuestsApiService);
  private readonly destroyRef = inject(DestroyRef);
  readonly propertyCtx = inject(PropertyContextService);

  private readonly routePropId = toSignal(
    this.route.queryParamMap.pipe(
      map((params) => Number(params.get('prop_id') ?? '0')),
      distinctUntilChanged(),
    ),
    { initialValue: 0 }
  );

  readonly selectedPropId = computed(() => this.routePropId());

  readonly viewState = signal<ViewState>('loading');
  readonly guests = signal<GuestItem[]>([]);
  readonly total = signal(0);
  readonly page = signal(1);
  readonly pageSize = signal(20);
  readonly hasNext = signal(false);
  readonly searchQuery = signal('');
  readonly message = signal('');
  readonly errorMessage = signal('');

  private loadGuests(propId: number, q: string, p: number): void {
    this.viewState.set('loading');
    this.api.listGuests(propId, q, p, this.pageSize()).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (res: GuestsResponse) => {
        this.guests.set(res.items);
        this.total.set(res.total);
        this.page.set(res.page);
        this.hasNext.set(res.has_next);
        this.viewState.set('success');
      },
      error: () => {
        this.viewState.set('error');
        this.errorMessage.set('No se pudieron cargar los huéspedes.');
      },
    });
  }

  constructor() {
    effect(() => {
      const propId = this.selectedPropId();
      if (!propId) {
        this.viewState.set('empty');
        this.guests.set([]);
        this.total.set(0);
        this.propertyCtx.clear();
        return;
      }
      this.loadGuests(propId, this.searchQuery(), 1);
    });

    // Auto-navigate in single-hotel mode
    effect(() => {
      if (this.propertyCtx.ready() && this.propertyCtx.singleHotelMode()) {
        const propId = this.propertyCtx.currentPropId();
        if (propId && !this.routePropId()) {
          void this.router.navigate([], {
            relativeTo: this.route,
            queryParams: { prop_id: propId },
          });
        }
      }
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    if (!event.propId) this.propertyCtx.clear();
    this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: event.label || null },
    });
  }

  onSearch(): void {
    const propId = this.selectedPropId();
    if (!propId) return;
    this.loadGuests(propId, this.searchQuery(), 1);
  }

  prevPage(): void {
    const propId = this.selectedPropId();
    if (!propId || this.page() <= 1) return;
    this.loadGuests(propId, this.searchQuery(), this.page() - 1);
  }

  nextPage(): void {
    const propId = this.selectedPropId();
    if (!propId || !this.hasNext()) return;
    this.loadGuests(propId, this.searchQuery(), this.page() + 1);
  }

  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize())));

  /** Format currency helper. */
  _money(value: number): string {
    return `$${value.toFixed(2)}`;
  }
}
