import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { RouterLink } from '@angular/router';

import { FavoritesService } from '../../../../core/favorites/favorites.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HotelCardComponent } from '../../components/hotel-card/hotel-card';
import { mapHotelSearchItems } from '../../mappers/hotel-search.mapper';
import type { HotelSearchResult } from '../../models/hotel-search.model';
import type { HotelSearchDto } from '../../models/hotel-search.dto';

@Component({
  selector: 'app-favorites-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    HotelCardComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    RouterLink,
  ],
  templateUrl: './favorites-page.html',
  styleUrl: './favorites-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FavoritesPageComponent {
  private readonly favorites = inject(FavoritesService);

  /** Signal with the current favorite IDs as a Set. */
  readonly favIds = this.favorites.favoriteIds;

  /** Comma-separated IDs string for the API query param. */
  private readonly idsParam = computed(() => {
    const ids = [...this.favIds()];
    return ids.length ? ids.join(',') : '';
  });

  /** httpResource that fetches hotel data for the user's favorite IDs. */
  readonly hotelsRes = httpResource<HotelSearchDto>(
    () => this.idsParam()
      ? `/api/hotels/availability?prop_ids=${this.idsParam()}&page_size=20`
      : undefined,
  );

  /** Computed list of HotelSearchResult items from the API response. */
  readonly items = computed<HotelSearchResult[]>(() => {
    const data = this.hotelsRes.value();
    if (!data?.items) return [];
    return mapHotelSearchItems(data);
  });

  /** Loading state derived from httpResource. */
  readonly loading = this.hotelsRes.isLoading;

  /** Error state derived from httpResource. */
  readonly hasError = computed(() => this.hotelsRes.error() !== undefined && !this.loading());

  /** View state for UI rendering. */
  readonly viewState = computed<ViewState>(() => {
    if (this.loading()) return 'loading';
    if (this.hasError()) return 'error';
    if (!this.favIds().size) return 'empty';
    if (this.items().length === 0) return 'empty';
    return 'success';
  });

  /** Count of favorites for display. */
  readonly favoriteCount = computed(() => this.favIds().size);
}
