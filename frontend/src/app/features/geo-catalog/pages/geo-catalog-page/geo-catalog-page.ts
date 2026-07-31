import { LowerCasePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { GeoCatalogApiService, type GeoEntry, type GeoListResponse } from '../../services/geo-catalog-api.service';

// ─── Local wire types for visitor-dataset endpoints ───────────────────────
// Each /visitor-* endpoint returns `{ items: T[] }` of a different shape.
interface VisitorCountryItem {
  visitor_location_country_id: number;
  country_display_name: string;
}
interface VisitorDestinationItem {
  srch_destination_id: number;
  destination_display_name: string;
}
interface VisitorSiteItem {
  site_id: number;
  site_display_name: string;
}
interface VisitorHotelItem {
  prop_id: number;
  hotel_name: string;
}
type VisitorListResponse<T> = { items: T[] };
// ──────────────────────────────────────────────────────────────────────────

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

  /** Reactive queryParams bridge — toSignal keeps URL the source of truth. */
  private readonly qp = toSignal(this.route.queryParamMap, {
    initialValue: this.route.snapshot.queryParamMap,
  });

  readonly viewState = computed<ViewState>(() => {
    const v = this.geoResource.value();
    if (this.geoResource.isLoading() && !v) return 'loading';
    const err = this.geoResource.error();
    if (err) return 'error';
    return v?.items.length ? 'success' : 'empty';
  });

  readonly data = computed(() => this.geoResource.value() ?? null);
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

  /**
   * Type-aware URL resolver — picks the right endpoint for each ``activeType``
   * value and sets up the page/q fetch. Visitor dimension endpoints return the
   * full list (no server-side filter/pag), so this is a 1-call chain via
   * httpResource with type-driven client-side ``applyLocalFilters()``.
   */
  readonly geoResource = httpResource<GeoListResponse>(() => {
    const page = Number(this.qp().get('page') ?? '1');
    const type = this.qp().get('type') || 'visitor-country';
    const q = this.qp().get('q') || '';

    // Visitor dimension types — full-list endpoint, paginate client-side.
    if (type === 'visitor-country' || type === 'visitor-destination' || type === 'visitor-site' || type === 'visitor-hotel') {
      this.activeType.set(type);
      return this.urlForVisitorType(type, q, page);
    }

    // Generic catalog (geo-catalog collection) — server-side filter/pag.
    this.activeType.set(type);
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (page > 1) params.set('page', String(page));
    const qs = params.toString();
    return qs ? `/api/management/geo-catalog?type=${type}&${qs}` : `/api/management/geo-catalog?type=${type}`;
  }, {
    parse: (raw: unknown) => {
      const page = Number(this.qp().get('page') ?? '1');
      const type = this.qp().get('type') || 'visitor-country';
      const q = this.qp().get('q') || '';
      const items = this.extractGeoEntries(raw, type);
      return this.applyLocalFilters(items, q, page);
    },
  });

  /**
   * Build URL for one of the visitor dimension endpoints and let httpResource
   * fire the GET; the parse callback adapts the response via
   * ``extractGeoEntries()`` + ``applyLocalFilters()``.
   */
  private urlForVisitorType(type: string, q: string, page: number): string {
    switch (type) {
      case 'visitor-country': return '/api/visitor/countries';
      case 'visitor-destination': return '/api/visitor/destinations';
      case 'visitor-site': return '/api/visitor/sites';
      case 'visitor-hotel': return '/api/visitor/hotels';
      default: return '/api/visitor/countries';
    }
  }

  private extractGeoEntries(raw: unknown, type: string): GeoEntry[] {
    const visitList = (raw as { items?: unknown[] })?.items ?? [];
    return visitList.map((itemUnknown) => {
      const item = itemUnknown as Record<string, unknown>;
      let id = '';
      let name = '';
      if (type === 'visitor-country') {
        id = String(item['visitor_location_country_id']);
        name = String(item['country_display_name'] ?? '');
      } else if (type === 'visitor-destination') {
        id = String(item['srch_destination_id']);
        name = String(item['destination_display_name'] ?? '');
      } else if (type === 'visitor-site') {
        id = String(item['site_id']);
        name = String(item['site_display_name'] ?? '');
      } else if (type === 'visitor-hotel') {
        id = String(item['prop_id']);
        name = String(item['hotel_name'] ?? '');
      }
      return {
        id,
        type,
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
  }

  constructor() {
    // No httpResource lifecycle hooks needed — the resource itself drives
    // viewState + data via its computed fields. Initial side-effect to keep
    // activeType in sync when type changes externally:
    effect(() => {
      const type = this.qp().get('type') || 'visitor-country';
      if (this.activeType() !== type) this.activeType.set(type);
    }, { allowSignalWrites: true });
  }

  private applyLocalFilters(items: GeoEntry[], q: string, page: number): GeoListResponse {
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

    let obs: Observable<unknown>;
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
      error: (err: unknown) => {
        const detail = (err as { error?: { detail?: string }; message?: string })?.error?.detail
          ?? (err as { message?: string })?.message
          ?? 'Error al guardar';
        this.toast.error(detail);
      },
    });
  }

  deleteEntry(entryId: string, name: string): void {
    // Left empty for compatibility as deletes are disabled for visitor dimensions
  }

  private refresh(): void {
    // Removed legacy sub-pipeline; reload via the httpResource.
    this.geoResource.reload();
  }

  typeIcon(type: string): string {
    return ENTRY_TYPES.find((t) => t.value === type)?.icon || 'public';
  }

  typeLabel(type: string): string {
    return ENTRY_TYPES.find((t) => t.value === type)?.label || type;
  }
}
