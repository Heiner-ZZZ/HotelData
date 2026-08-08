import { HttpErrorResponse, HttpParams, httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { OwnershipApiService } from '../../services/ownership-api.service';
import type { OwnershipUserDetail, HotelSearchResult } from '../../models/ownership.model';
import type { OwnershipUserDetailResponseDto } from '../../models/ownership.dto';
import { mapHotelSearchResponse, mapOwnershipUserDetailResponse } from '../../mappers/ownership.mapper';
import { roleLabel } from '../../../../core/auth/role-labels';

interface HotelSearchResponse {
  items: HotelSearchResult[];
  hasNext: boolean;
}

@Component({
  selector: 'app-ownership-user-detail-page',
  imports: [
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
    ReactiveFormsModule,
    RouterLink,
  ],
  templateUrl: './ownership-user-detail-page.html',
  styleUrl: './ownership-user-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class OwnershipUserDetailPageComponent {
  private readonly api = inject(OwnershipApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly user = signal<OwnershipUserDetail | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');
  readonly saving = signal(false);
  readonly roleLabel = roleLabel;

  // `nonNullable: true` keeps `searchControl.value` typed as `string` (not
  // `string | null`), so the debounce effect can pipe `searchValue()` into
  // `debouncedSearchValue.set(...)` without a null-check.
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly searching = signal(false);
  readonly searchResults = signal<HotelSearchResult[]>([]);
  readonly searchPage = signal(1);
  readonly hasMoreResults = signal(false);
  /** Backing store for `currentQuery` so `loadMore` (legacy callers) keep working. */
  private currentQuery = '';

  // ── Reactive route param → httpResource (re-fires on userId change) ──
  private readonly paramMap = toSignal(this.route.paramMap, {
    initialValue: this.route.snapshot.paramMap,
  });
  readonly userId = computed(() => this.paramMap().get('userId') ?? '');

  readonly detailResource = httpResource<OwnershipUserDetail>(() => {
    const id = this.userId();
    return id ? `/api/admin/ownership/users/${id}` : undefined;
  }, {
    // El API envuelve el detalle en `{ user: ... }` con snake_case. Sin este
    // parse, `user()` quedaba en el wrapper crudo (sin `hotels`) y el template
    // reventaba con `Cannot read properties of undefined (reading 'length')`.
    parse: (dto) => mapOwnershipUserDetailResponse(dto as OwnershipUserDetailResponseDto),
  });

  /** Debounced search term (mirrors `searchControl.valueChanges` after 350ms idle). */
  private readonly debouncedSearchValue = signal('');

  /**
   * Reactive `valueChanges` of the search input. Initialised synchronously from
   * the FormControl's current `.value` so the debounce effect fires immediately.
   */
  private readonly searchValue = toSignal(this.searchControl.valueChanges, {
    initialValue: this.searchControl.value ?? '',
  });

  readonly searchResource = httpResource<HotelSearchResponse>(() => {
    const userId = this.userId();
    if (!userId) return undefined;
    const term = this.debouncedSearchValue();
    const page = this.searchPage();
    const params = new HttpParams()
      .set('q', term)
      .set('page', String(page))
      .set('page_size', '20');
    return {
      // URL matches `OwnershipApiService.searchHotels(...)` which uses
      // `${base}/hotels/search` where base = `${apiConfig.baseUrl}/admin/ownership`.
      // The path is relative, mirroring how `detailResource` builds its URL.
      url: `/api/admin/ownership/hotels/search`,
      method: 'GET' as const,
      params,
      withCredentials: true,
    };
  }, {
    // Use the canonical snake_case → camelCase mapper. Mirrors the legacy
    // `OwnershipApiService.searchHotels(...).pipe(map(dto => mapHotelSearchResponse(dto)))`
    // path exactly, so the response shape for the template + helpers stays
    // bit-identical to before.
    parse: (dto) => mapHotelSearchResponse(dto as Parameters<typeof mapHotelSearchResponse>[0]),
  });

  /**
   * Id-gated sync from httpResource → user signal. Triggered exactly once
   * per id change so optimistic updates from toggleHotel / saveHotels
   * (which write user.set(...) directly) are NOT replayed back into the
   * user signal by the httpResource-to-signal effect.
   */
  private lastInitializedId: string | null = null;

  constructor() {
    effect(() => {
      const detail = this.detailResource.value();
      const id = this.userId();
      const err = this.detailResource.error();

      if (!id) return;
      if (err) {
        this.viewState.set('error');
        return;
      }
      if (!detail && this.detailResource.isLoading()) {
        this.viewState.set('loading');
        return;
      }
      if (detail && id !== this.lastInitializedId) {
        this.lastInitializedId = id;
        this.user.set(detail);
        this.viewState.set('success');
      }
    }, { allowSignalWrites: true });

    // ── Replace debounceTime(350) + distinctUntilChanged + tap: mirror searchValue
    // into debouncedSearchValue after 350ms idle. `onCleanup` cancels any pending
    // timer when the user types again (trailing-edge debounce semantic). The tap
    // side-effects (`searching`, `searchPage=1`, `currentQuery=...`) move into
    // the timer callback — same observable behaviour as the legacy rxjs chain.
    effect((onCleanup) => {
      const q = this.searchValue();
      const timer = setTimeout(() => {
        this.debouncedSearchValue.set(q);
        this.searching.set(true);
        this.searchPage.set(1);
        this.currentQuery = q || '';
      }, 350);
      onCleanup(() => clearTimeout(timer));
    });

    // ── Bridge: searchResource.value() → component state ──
    // Page=1 → REPLACE results; page>1 → APPEND (mirrors legacy loadMore merge).
    // [FIX] `untracked()` around the read breaks the self-write re-entrancy
    // (effect would otherwise depend on `searchResults` AND write to it in
    // the same pass, triggering NG0600 producerRecomputeValue storm).
    effect(() => {
      const r = this.searchResource.value();
      if (!r) return;
      if (this.searchPage() === 1) {
        this.searchResults.set(r.items);
      } else {
        const existing = new Set(
          untracked(() => this.searchResults()).map((h) => h.propId),
        );
        const fresh = r.items.filter((item) => !existing.has(item.propId));
        this.searchResults.update((prev) => [...prev, ...fresh]);
      }
      this.hasMoreResults.set(r.hasNext);
      this.searching.set(false);
    });

    // ── Bridge: searchResource.error() → graceful empty state ──
    effect(() => {
      const err = this.searchResource.error();
      if (!err) return;
      this.searchResults.set([]);
      this.hasMoreResults.set(false);
      this.searching.set(false);
    });
  }

  isSelected(propId: number): boolean {
    return this.user()?.hotels.some((h) => h.propId === propId) ?? false;
  }

  toggleHotel(hotel: HotelSearchResult) {
    const u = this.user();
    if (!u) return;

    if (this.isSelected(hotel.propId)) {
      this.removeHotel(hotel.propId);
    } else {
      this.user.set({
        ...u,
        hotels: [...u.hotels, { propId: hotel.propId, label: hotel.label, countryId: hotel.countryId ?? null }],
        assignedHotels: [...u.assignedHotels, hotel.propId]
      });
    }
  }

  removeHotel(propId: number) {
    const u = this.user();
    if (!u) return;
    this.user.set({
      ...u,
      hotels: u.hotels.filter((h) => h.propId !== propId),
      assignedHotels: u.assignedHotels.filter((id) => id !== propId)
    });
  }

  /** `httpResource` auto-refires when `searchPage()` increments. */
  loadMore() {
    if (!this.hasMoreResults() || this.searching()) return;
    this.searching.set(true);
    this.searchPage.update((p) => p + 1);
  }

  saveHotels() {
    const u = this.user();
    if (!u || this.saving()) return;
    this.saving.set(true);
    this.message.set('');
    this.errorMessage.set('');

    this.api.updateAssignedHotels(this.userId(), u.assignedHotels)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.saving.set(false);
          if (result.ok) {
            this.message.set(result.message);
            this.user.set({ ...u, hotels: result.hotels });
          } else {
            this.errorMessage.set(result.message);
          }
        },
        error: (err: ApiError) => {
          this.saving.set(false);
          this.errorMessage.set(err.message || 'Error al guardar.');
        }
      });
  }
}
