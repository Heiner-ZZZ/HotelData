import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { HotelDetailViewModel } from '../../models/hotel-detail.model';
import { HotelDetailApiService } from '../../services/hotel-detail-api.service';

@Component({
  selector: 'app-hotel-detail-page',
  standalone: true,
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    RouterLink,
    StatusBadgeComponent
  ],
  templateUrl: './hotel-detail-page.html',
  styleUrl: './hotel-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly hotelDetailApi = inject(HotelDetailApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<HotelDetailViewModel | null>(null);
  readonly pageDescription = computed(() => {
    const vm = this.viewModel();
    return vm
      ? `ID propiedad: ${vm.propId}. Esta vista Angular consume datos reales del backend sin alterar la ruta legacy.`
      : 'Cargando detalle de la propiedad.';
  });

  constructor() {
    this.route.paramMap
      .pipe(
        map((params) => Number(params.get('hotelId'))),
        switchMap((hotelId) => {
          this.viewState.set('loading');
          return this.hotelDetailApi.getHotelDetail(hotelId);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (viewModel) => {
          this.viewModel.set(viewModel);
          this.viewState.set('success');
        },
        error: () => {
          this.viewModel.set(null);
          this.viewState.set('error');
        }
      });
  }
}
