import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged, switchMap, tap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { OwnershipApiService } from '../../services/ownership-api.service';
import type { OwnershipUserDetail, HotelSearchResult } from '../../models/ownership.model';
import { roleLabel } from '../../../../core/auth/role-labels';

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

  readonly searchControl = new FormControl('');
  readonly searching = signal(false);
  readonly searchResults = signal<HotelSearchResult[]>([]);
  readonly searchPage = signal(1);
  readonly hasMoreResults = signal(false);
  private currentQuery = '';

  private userId = '';

  constructor() {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(params => {
      const id = params.get('userId');
      if (id) {
        this.userId = id;
        this.loadUser();
      }
    });

    this.searchControl.valueChanges.pipe(
      debounceTime(350),
      distinctUntilChanged(),
      tap((q) => {
        this.searching.set(true);
        this.searchPage.set(1);
        this.currentQuery = q || '';
      }),
      switchMap((q) => this.api.searchHotels(q || '', 1, 20)),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (result) => {
        this.searchResults.set(result.items);
        this.hasMoreResults.set(result.hasNext);
        this.searching.set(false);
      },
      error: () => {
        this.searchResults.set([]);
        this.hasMoreResults.set(false);
        this.searching.set(false);
      }
    });
  }

  private loadUser() {
    this.viewState.set('loading');
    this.api.getUserDetail(this.userId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (detail) => {
        this.user.set(detail);
        this.viewState.set('success');
      },
      error: () => {
        this.viewState.set('error');
      }
    });
  }

  isSelected(propId: number): boolean {
    return this.user()?.hotels.some(h => h.propId === propId) ?? false;
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
      hotels: u.hotels.filter(h => h.propId !== propId),
      assignedHotels: u.assignedHotels.filter(id => id !== propId)
    });
  }

  loadMore() {
    const nextPage = this.searchPage() + 1;
    this.searchPage.set(nextPage);
    this.api.searchHotels(this.currentQuery, nextPage, 20)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.searchResults.update(prev => [...prev, ...result.items]);
          this.hasMoreResults.set(result.hasNext);
        }
      });
  }

  saveHotels() {
    const u = this.user();
    if (!u || this.saving()) return;
    this.saving.set(true);
    this.message.set('');
    this.errorMessage.set('');

    this.api.updateAssignedHotels(this.userId, u.assignedHotels)
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
