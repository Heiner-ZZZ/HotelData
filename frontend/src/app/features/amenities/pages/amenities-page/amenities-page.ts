import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { mapAmenitiesPayload } from '../../mappers/amenities.mapper';
import type { AmenityCategoryViewModel, AmenitiesViewModel } from '../../models/amenities.model';
import { AmenitiesApiService } from '../../services/amenities-api.service';
import { ActiveAmenitiesSummaryComponent } from '../../components/active-amenities-summary/active-amenities-summary';
import { AmenityCategoryPanelComponent } from '../../components/amenity-category-panel/amenity-category-panel';

@Component({
  selector: 'app-amenities-page',
  imports: [
    ActiveAmenitiesSummaryComponent,
    AmenityCategoryPanelComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule
  ],
  templateUrl: './amenities-page.html',
  styleUrl: './amenities-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AmenitiesPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(AmenitiesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<AmenitiesViewModel | null>(null);
  readonly selectedAmenities = signal<string[]>([]);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  readonly utilityForm = this.formBuilder.nonNullable.group({
    search: [''],
    manualAmenity: ['']
  });

  readonly selectedLookup = computed(() => new Set(this.selectedAmenities().map((item) => item.toLowerCase())));

  readonly filteredCategories = computed(() => {
    const vm = this.viewModel();
    const search = this.utilityForm.controls.search.value.trim().toLowerCase();
    if (!vm) {
      return [] as AmenityCategoryViewModel[];
    }
    if (!search) {
      return vm.categories;
    }
    return vm.categories
      .map((category) => ({
        ...category,
        items: category.items.filter((item) => item.label.toLowerCase().includes(search))
      }))
      .filter((category) => category.items.length);
  });

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        switchMap((propId) => {
          this.viewState.set('loading');
          this.message.set('');
          this.errorMessage.set('');
          return propId > 0 ? this.api.getAmenities(propId) : of(null);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (amenities) => {
          if (amenities) {
            this.viewModel.set(amenities);
            this.selectedAmenities.set(amenities.activeAmenities);
            this.selectedPropId.set(amenities.propId);
            this.selectedLabel.set(amenities.hotelName);
            this.viewState.set('success');
          } else {
            this.viewModel.set(null);
            this.selectedAmenities.set([]);
            this.viewState.set('empty');
          }
        },
        error: () => this.viewState.set('error')
      });
  }

  onPropSelected(propId: number) {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null }
    });
  }

  toggleAmenity(label: string) {
    const normalized = label.trim();
    if (!normalized) {
      return;
    }
    const current = this.selectedAmenities();
    const lookup = new Set(current.map((item) => item.toLowerCase()));
    if (lookup.has(normalized.toLowerCase())) {
      this.selectedAmenities.set(current.filter((item) => item.toLowerCase() !== normalized.toLowerCase()));
    } else {
      this.selectedAmenities.set([...current, normalized]);
    }
  }

  addManualAmenity() {
    const value = this.utilityForm.controls.manualAmenity.value.trim();
    if (!value) {
      return;
    }
    this.toggleAmenity(value);
    this.utilityForm.controls.manualAmenity.setValue('');
  }

  saveAmenities() {
    const current = this.viewModel();
    if (!current) {
      return;
    }
    this.api
      .saveAmenities(mapAmenitiesPayload(current.propId, this.selectedAmenities()))
      .pipe(
        switchMap(() => this.api.getAmenities(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (amenities) => {
          this.viewModel.set(amenities);
          this.selectedAmenities.set(amenities.activeAmenities);
          this.message.set('Servicios actualizados');
          this.errorMessage.set('');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible guardar los servicios.');
          this.message.set('');
        }
      });
  }
}
