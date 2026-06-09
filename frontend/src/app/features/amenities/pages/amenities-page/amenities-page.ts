import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, forkJoin, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { mapAmenitiesPayload } from '../../mappers/amenities.mapper';
import type { AmenityCategoryViewModel, AmenitiesPropertyOption, AmenitiesViewModel } from '../../models/amenities.model';
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
  readonly propertyOptions = signal<AmenitiesPropertyOption[]>([]);
  readonly selectedAmenities = signal<string[]>([]);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectorForm = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]]
  });

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
          return forkJoin({
            options: this.api.getOptions(propId > 0 ? propId : undefined),
            amenities: propId > 0 ? this.api.getAmenities(propId) : of(null)
          });
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ options, amenities }) => {
          this.propertyOptions.set(options);
          if (!this.selectorForm.controls.propId.value && options.length) {
            this.selectorForm.controls.propId.setValue(options[0].propId);
          }
          if (amenities) {
            this.viewModel.set(amenities);
            this.selectedAmenities.set(amenities.activeAmenities);
            this.selectorForm.controls.propId.setValue(amenities.propId, { emitEvent: false });
            this.viewState.set('success');
          } else {
            this.viewModel.set(null);
            this.selectedAmenities.set([]);
            this.viewState.set(options.length ? 'empty' : 'success');
          }
        },
        error: () => this.viewState.set('error')
      });
  }

  selectProperty() {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: this.selectorForm.controls.propId.value || null }
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
