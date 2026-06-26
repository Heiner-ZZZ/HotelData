import { SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { GeoCatalogApiService, type GeoEntry, type GeoListResponse } from '../../services/geo-catalog-api.service';

const ENTRY_TYPES = [
  { value: 'country', label: 'Países', icon: 'public' },
  { value: 'state', label: 'Estados / Provincias', icon: 'map' },
  { value: 'city', label: 'Ciudades', icon: 'location_city' },
  { value: 'destination', label: 'Destinos turísticos', icon: 'tour' },
] as const;

@Component({
  selector: 'app-geo-catalog-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, SlicePipe],
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

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<GeoListResponse | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly activeType = signal<string>('country');
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
    latitude: [<number | null>null],
    longitude: [<number | null>null],
  });

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          type: params.get('type') || 'country',
          q: params.get('q') || '',
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.type === b.type && a.q === b.q),
        switchMap(({ page, type, q }) => {
          this.viewState.set('loading');
          this.activeType.set(type);
          return this.api.listEntries(type || undefined, undefined, q || undefined, page);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
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
    if (this.showCreateForm()) {
      this.createForm.reset({
        code: '',
        name: '',
        countryCode: '',
        stateCode: '',
        category: '',
        isoCode: '',
        latitude: null,
        longitude: null,
      });
    }
  }

  startEdit(item: GeoEntry): void {
    this.editingId.set(item.id);
    this.showCreateForm.set(true);
    this.createForm.setValue({
      code: item.code,
      name: item.name,
      countryCode: item.countryCode || '',
      stateCode: item.stateCode || '',
      category: item.category || '',
      isoCode: item.isoCode || '',
      latitude: item.latitude,
      longitude: item.longitude,
    });
  }

  cancelForm(): void {
    this.showCreateForm.set(false);
    this.editingId.set(null);
  }

  submitEntry(): void {
    if (this.createForm.invalid) return;
    const val = this.createForm.getRawValue();
    const editId = this.editingId();
    const obs = editId
      ? this.api.updateEntry(editId, {
          name: val.name || undefined,
          country_code: val.countryCode || undefined,
          state_code: val.stateCode || undefined,
          category: val.category || undefined,
          iso_code: val.isoCode || undefined,
          latitude: val.latitude,
          longitude: val.longitude,
        })
      : this.api.createEntry({
          type: this.activeType(),
          code: val.code,
          name: val.name,
          country_code: val.countryCode || undefined,
          state_code: val.stateCode || undefined,
          category: val.category || undefined,
          iso_code: val.isoCode || undefined,
          latitude: val.latitude,
          longitude: val.longitude,
        });

    obs.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.message.set(editId ? 'Entrada actualizada' : 'Entrada creada exitosamente');
        this.errorMessage.set('');
        this.showCreateForm.set(false);
        this.editingId.set(null);
        this.refresh();
      },
      error: (err) => {
        this.errorMessage.set(err.error?.detail || err.message || 'Error al guardar');
        this.message.set('');
      },
    });
  }

  deleteEntry(entryId: string, name: string): void {
    if (!confirm(`¿Eliminar "${name}"? Esta acción no se puede deshacer.`)) return;
    this.api
      .deleteEntry(entryId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.message.set('Entrada eliminada');
          this.errorMessage.set('');
          this.refresh();
        },
        error: (err) => {
          this.errorMessage.set(err.error?.detail || err.message || 'Error al eliminar');
          this.message.set('');
        },
      });
  }

  private refresh(): void {
    const current = this.data();
    if (!current) return;
    this.viewState.set('loading');
    this.api
      .listEntries(this.activeType() || undefined, undefined, undefined, current.page)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
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
