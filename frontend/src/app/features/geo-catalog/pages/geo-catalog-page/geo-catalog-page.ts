import { LowerCasePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { GeoCatalogApiService, type GeoEntry, type GeoListResponse } from '../../services/geo-catalog-api.service';

const ENTRY_TYPES = [
  { value: 'visitor-country', label: 'Países del Dataset (IDs)', icon: 'dataset' },
  { value: 'visitor-destination', label: 'Destinos del Dataset (IDs)', icon: 'tour' },
  { value: 'visitor-site', label: 'Canales / Sitios del Dataset (IDs)', icon: 'settings_ethernet' },
  { value: 'visitor-hotel', label: 'Hoteles del Dataset (IDs)', icon: 'hotel' },
] as const;

@Component({
  selector: 'app-geo-catalog-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, LowerCasePipe],
  templateUrl: './geo-catalog-page.html',
  styleUrl: './geo-catalog-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GeoCatalogPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(GeoCatalogApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly toast = inject(ToastService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<GeoListResponse | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly activeType = signal<string>('visitor-country');
  readonly showCreateForm = signal(false);
  readonly editingId = signal<string | null>(null);
  readonly entryTypes = [...ENTRY_TYPES];

  readonly createForm = this.formBuilder.nonNullable.group({
    code: ['', Validators.required],
    name: ['', Validators.required],
    countryCode: [''],
    stateCode: [''],
    category: [''],
    isoCode: [''],
    latitude: [(null as number | null)],
    longitude: [(null as number | null)],
  });

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          type: params.get('type') || 'visitor-country',
          q: params.get('q') || '',
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.type === b.type && a.q === b.q),
        switchMap(({ page, type, q }) => {
          this.viewState.set('loading');
          this.activeType.set(type);

          let obs: any;
          if (type === 'visitor-country') {
            obs = this.api.listVisitorCountries().pipe(
              map((res: any) => {
                const items = res.items.map((item: any) => ({
                  id: String(item.visitor_location_country_id),
                  type: 'visitor-country',
                  code: String(item.visitor_location_country_id),
                  name: item.country_display_name,
                  countryCode: '',
                  stateCode: '',
                  category: '',
                  isoCode: '',
                  latitude: null,
                  longitude: null,
                  isActive: true,
                  createdAt: '',
                  updatedAt: null,
                }));
                return this.applyLocalFilters(items, q, page);
              })
            );
          } else if (type === 'visitor-destination') {
            obs = this.api.listVisitorDestinations().pipe(
              map((res: any) => {
                const items = res.items.map((item: any) => ({
                  id: String(item.srch_destination_id),
                  type: 'visitor-destination',
                  code: String(item.srch_destination_id),
                  name: item.destination_display_name,
                  countryCode: '',
                  stateCode: '',
                  category: '',
                  isoCode: '',
                  latitude: null,
                  longitude: null,
                  isActive: true,
                  createdAt: '',
                  updatedAt: null,
                }));
                return this.applyLocalFilters(items, q, page);
              })
            );
          } else if (type === 'visitor-site') {
            obs = this.api.listVisitorSites().pipe(
              map((res: any) => {
                const items = res.items.map((item: any) => ({
                  id: String(item.site_id),
                  type: 'visitor-site',
                  code: String(item.site_id),
                  name: item.site_display_name,
                  countryCode: '',
                  stateCode: '',
                  category: '',
                  isoCode: '',
                  latitude: null,
                  longitude: null,
                  isActive: true,
                  createdAt: '',
                  updatedAt: null,
                }));
                return this.applyLocalFilters(items, q, page);
              })
            );
          } else if (type === 'visitor-hotel') {
            obs = this.api.listVisitorHotels().pipe(
              map((res: any) => {
                const items = res.items.map((item: any) => ({
                  id: String(item.prop_id),
                  type: 'visitor-hotel',
                  code: String(item.prop_id),
                  name: item.hotel_name,
                  countryCode: '',
                  stateCode: '',
                  category: '',
                  isoCode: '',
                  latitude: null,
                  longitude: null,
                  isActive: true,
                  createdAt: '',
                  updatedAt: null,
                }));
                return this.applyLocalFilters(items, q, page);
              })
            );
          } else {
            obs = this.api.listEntries(type || undefined, undefined, q || undefined, page);
          }
          return obs;
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data: any) => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  private applyLocalFilters(items: any[], q: string, page: number): GeoListResponse {
    if (q) {
      const pattern = q.toLowerCase();
      items = items.filter(
        (i) =>
          i.name.toLowerCase().includes(pattern) ||
          i.code.toLowerCase().includes(pattern)
      );
    }
    const pageSize = 50;
    const total = items.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const startIdx = (page - 1) * pageSize;
    const paginated = items.slice(startIdx, startIdx + pageSize);
    return {
      items: paginated,
      total,
      page,
      pageSize,
      totalPages,
      hasNext: page * pageSize < total,
      hasPrev: page > 1,
    };
  }

  setTypeFilter(type: string): void {
    this.activeType.set(type);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { type, page: null, q: null },
    });
  }

  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: page > 1 ? page : null },
    });
  }

  toggleCreateForm(): void {
    this.showCreateForm.update((v) => !v);
    this.editingId.set(null);
  }

  startEdit(item: GeoEntry): void {
    this.editingId.set(item.id);
    this.showCreateForm.set(true);
    this.createForm.patchValue({
      code: item.code,
      name: item.name,
    });
  }

  namePlaceholder(): string {
    const type = this.activeType();
    if (type === 'visitor-country') return 'Ej: ECUADOR, MÉXICO, COLOMBIA';
    if (type === 'visitor-destination') return 'Ej: Quito Centro, Cancún Playas, Galápagos';
    if (type === 'visitor-site') return 'Ej: Expedia, Booking.com, Sitio Web Oficial';
    if (type === 'visitor-hotel') return 'Ej: Hotel Plaza Grande, Hotel Decameron';
    return 'Ingrese el nuevo nombre...';
  }

  cancelForm(): void {
    this.showCreateForm.set(false);
    this.editingId.set(null);
  }

  submitEntry(): void {
    if (this.createForm.invalid) return;
    const val = this.createForm.getRawValue();
    const editId = this.editingId();
    if (!editId) return;

    let obs: any;
    if (this.activeType() === 'visitor-country') {
      obs = this.api.updateVisitorCountry(Number(editId), val.name);
    } else if (this.activeType() === 'visitor-destination') {
      obs = this.api.updateVisitorDestination(Number(editId), val.name);
    } else if (this.activeType() === 'visitor-site') {
      obs = this.api.updateVisitorSite(Number(editId), val.name);
    } else if (this.activeType() === 'visitor-hotel') {
      obs = this.api.updateVisitorHotel(Number(editId), val.name);
    } else {
      return;
    }

    obs.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.toast.success('Nombre actualizado correctamente');
        this.showCreateForm.set(false);
        this.editingId.set(null);
        this.refresh();
      },
      error: (err: any) => {
        this.toast.error(err.error?.detail || err.message || 'Error al guardar');
      },
    });
  }

  deleteEntry(entryId: string, name: string): void {
    // Left empty for compatibility as deletes are disabled for visitor dimensions
  }

  private refresh(): void {
    const current = this.data();
    if (!current) return;
    this.viewState.set('loading');
    
    let listObs: any;
    if (this.activeType() === 'visitor-country') {
      listObs = this.api.listVisitorCountries();
    } else if (this.activeType() === 'visitor-destination') {
      listObs = this.api.listVisitorDestinations();
    } else if (this.activeType() === 'visitor-site') {
      listObs = this.api.listVisitorSites();
    } else if (this.activeType() === 'visitor-hotel') {
      listObs = this.api.listVisitorHotels();
    } else {
      return;
    }

    listObs.pipe(
      map((res: any) => {
        const items = res.items.map((item: any) => {
          let id = '';
          let name = '';
          if (this.activeType() === 'visitor-country') {
            id = String(item.visitor_location_country_id);
            name = item.country_display_name;
          } else if (this.activeType() === 'visitor-destination') {
            id = String(item.srch_destination_id);
            name = item.destination_display_name;
          } else if (this.activeType() === 'visitor-site') {
            id = String(item.site_id);
            name = item.site_display_name;
          } else if (this.activeType() === 'visitor-hotel') {
            id = String(item.prop_id);
            name = item.hotel_name;
          }
          return {
            id,
            type: this.activeType(),
            code: id,
            name,
            countryCode: '',
            stateCode: '',
            category: '',
            isoCode: '',
            latitude: null,
            longitude: null,
            isActive: true,
            createdAt: '',
            updatedAt: null,
          };
        });
        const q = this.route.snapshot.queryParams['q'] || '';
        return this.applyLocalFilters(items, q, current.page);
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (data: any) => {
        this.data.set(data);
        this.viewState.set(data.items.length ? 'success' : 'empty');
      },
      error: () => this.viewState.set('error'),
    });
  }

  typeIcon(type: string): string {
    return ENTRY_TYPES.find((t) => t.value === type)?.icon || 'public';
  }

  typeLabel(type: string): string {
    return ENTRY_TYPES.find((t) => t.value === type)?.label || type;
  }
}
