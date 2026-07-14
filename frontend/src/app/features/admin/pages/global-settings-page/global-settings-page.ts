import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type {
  PlatformConfig,
  HotelGlobalItem,
  TaxRate,
  CommissionRate,
} from '../../models/global-settings.model';
import type { PlatformConfigDto, TaxRateDto, CommissionRateDto } from '../../models/global-settings.dto';
import { GlobalSettingsApiService } from '../../services/global-settings-api.service';
import { mapPlatformConfig, mapTaxRate, mapCommissionRate } from '../../mappers/global-settings.mapper';

type ActiveTab = 'hotels' | 'taxes' | 'commissions' | 'config';

@Component({
  selector: 'app-global-settings-page',
  imports: [
    FormsModule,
    DatePipe,
    PageHeaderComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
  ],
  templateUrl: './global-settings-page.html',
  styleUrl: './global-settings-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GlobalSettingsPageComponent {
  private readonly api = inject(GlobalSettingsApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly destroyRef = inject(DestroyRef);
  private configInitialized = false;

  readonly activeTab = signal<ActiveTab>('hotels');

  // Platform Config
  readonly configResource = httpResource<PlatformConfig>(
    () => `/api/admin/global-settings/config`,
    { parse: (dto) => mapPlatformConfig(dto as PlatformConfigDto) },
  );
  readonly config = computed(() => this.configResource.value());
  readonly configState = computed(() => this.resourceState(this.configResource));
  readonly editCommission = signal(5.0);
  readonly editIva = signal(16.0);
  readonly configSaving = signal(false);
  readonly configMessage = signal('');

  // Hotels (kept manual because of pagination + search)
  readonly hotelsState = signal<ViewState>('loading');
  readonly hotels = signal<HotelGlobalItem[]>([]);
  readonly hotelsTotal = signal(0);
  readonly hotelsPage = signal(1);
  readonly hotelsPages = signal(1);
  readonly hotelSearch = signal('');
  readonly editingHotel = signal<number | null>(null);
  readonly editCountry = signal('');
  readonly editCity = signal('');
  readonly editProvince = signal('');
  readonly editGroup = signal('');
  readonly hotelSaving = signal(false);
  readonly hotelMessage = signal('');

  pagesArray(): number[] {
    return Array.from({ length: this.hotelsPages() }, (_, i) => i + 1);
  }

  // Tax Rates
  readonly taxRatesResource = httpResource<TaxRate[]>(
    () => `/api/admin/global-settings/tax-rates`,
    { parse: (dto) => (dto as { items: TaxRateDto[] }).items.map(mapTaxRate) },
  );
  readonly taxRates = computed(() => this.taxRatesResource.value() ?? []);
  readonly taxState = computed(() => this.arrayResourceState(this.taxRatesResource));
  readonly newTaxCountryId = signal<number | null>(null);
  readonly newTaxCountryName = signal('');
  readonly newTaxIva = signal(16.0);
  readonly editingTax = signal<number | null>(null);
  readonly editTaxIva = signal(16.0);
  readonly taxSaving = signal(false);
  readonly taxMessage = signal('');

  // Commission Rates
  readonly commissionRatesResource = httpResource<CommissionRate[]>(
    () => `/api/admin/global-settings/commission-rates`,
    { parse: (dto) => (dto as { items: CommissionRateDto[] }).items.map(mapCommissionRate) },
  );
  readonly commissionRates = computed(() => this.commissionRatesResource.value() ?? []);
  readonly commissionState = computed(() => this.arrayResourceState(this.commissionRatesResource));
  readonly newCommissionPropId = signal<number | null>(null);
  readonly newCommissionPct = signal(5.0);
  readonly editingCommission = signal<number | null>(null);
  readonly editCommissionPct = signal(5.0);
  readonly commissionSaving = signal(false);
  readonly commissionMessage = signal('');

  constructor() {
    this.loadHotels();

    effect(() => {
      const cfg = this.config();
      if (cfg && !this.configInitialized) {
        this.editCommission.set(cfg.defaultCommissionPct);
        this.editIva.set(cfg.defaultIvaPct);
        this.configInitialized = true;
      }
    });
  }

  private resourceState(resource: { error(): unknown; isLoading(): boolean; value(): unknown | undefined }): ViewState {
    if (resource.error()) return 'error';
    if (resource.isLoading()) return 'loading';
    return 'success';
  }

  private arrayResourceState<T>(resource: { error(): unknown; isLoading(): boolean; value(): T[] | undefined }): ViewState {
    if (resource.error()) return 'error';
    if (resource.isLoading()) return 'loading';
    return resource.value()?.length ? 'success' : 'empty';
  }

  setTab(tab: ActiveTab) {
    this.activeTab.set(tab);
  }

  // ─── Config ────────────────────────────────────────────────────

  saveConfig() {
    this.configSaving.set(true);
    this.configMessage.set('');
    this.api
      .updateConfig({
        default_commission_pct: this.editCommission(),
        default_iva_pct: this.editIva(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (cfg) => {
          this.configSaving.set(false);
          this.configMessage.set('Configuración guardada correctamente');
          this.editCommission.set(cfg.defaultCommissionPct);
          this.editIva.set(cfg.defaultIvaPct);
          this.configResource.reload();
        },
        error: () => {
          this.configSaving.set(false);
          this.configMessage.set('Error al guardar la configuración');
        },
      });
  }

  // ─── Hotels ────────────────────────────────────────────────────

  loadHotels() {
    this.hotelsState.set('loading');
    this.api
      .listHotels(this.hotelSearch(), this.hotelsPage())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (list) => {
          this.hotels.set(list.items);
          this.hotelsTotal.set(list.total);
          this.hotelsPages.set(list.totalPages);
          this.hotelsState.set(list.items.length ? 'success' : 'empty');
        },
        error: () => {
          this.hotelsState.set('error');
        },
      });
  }

  searchHotels() {
    this.hotelsPage.set(1);
    this.loadHotels();
  }

  goToHotelPage(page: number) {
    this.hotelsPage.set(page);
    this.loadHotels();
  }

  startEditHotel(hotel: HotelGlobalItem) {
    this.editingHotel.set(hotel.propId);
    this.editCountry.set(hotel.countryName);
    this.editCity.set(hotel.city);
    this.editProvince.set(hotel.province);
    this.editGroup.set(hotel.hotelGroup);
    this.hotelMessage.set('');
  }

  cancelEditHotel() {
    this.editingHotel.set(null);
  }

  saveHotel(propId: number) {
    this.hotelSaving.set(true);
    this.hotelMessage.set('');
    this.api
      .updateHotel(propId, {
        country_name: this.editCountry() || null,
        city: this.editCity() || null,
        province: this.editProvince() || null,
        hotel_group: this.editGroup() || null,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.hotelSaving.set(false);
          this.editingHotel.set(null);
          this.hotelMessage.set('Hotel actualizado correctamente');
          this.loadHotels();
        },
        error: () => {
          this.hotelSaving.set(false);
          this.hotelMessage.set('Error al actualizar el hotel');
        },
      });
  }

  // ─── Tax Rates ─────────────────────────────────────────────────

  addTaxRate() {
    const countryId = this.newTaxCountryId();
    if (countryId === null) return;
    this.taxSaving.set(true);
    this.taxMessage.set('');
    this.api
      .createTaxRate({
        country_id: countryId,
        country_name: this.newTaxCountryName(),
        iva_pct: this.newTaxIva(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.taxSaving.set(false);
          this.newTaxCountryId.set(null);
          this.newTaxCountryName.set('');
          this.newTaxIva.set(16.0);
          this.taxRatesResource.reload();
        },
        error: () => {
          this.taxSaving.set(false);
          this.taxMessage.set('Error al crear la tasa de IVA');
        },
      });
  }

  startEditTax(rate: TaxRate) {
    this.editingTax.set(rate.countryId);
    this.editTaxIva.set(rate.ivaPct);
    this.taxMessage.set('');
  }

  cancelEditTax() {
    this.editingTax.set(null);
  }

  saveTaxRate(countryId: number) {
    this.taxSaving.set(true);
    this.taxMessage.set('');
    this.api
      .updateTaxRate(countryId, { iva_pct: this.editTaxIva() })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.taxSaving.set(false);
          this.editingTax.set(null);
          this.taxRatesResource.reload();
        },
        error: () => {
          this.taxSaving.set(false);
          this.taxMessage.set('Error al actualizar la tasa de IVA');
        },
      });
  }

  async deleteTaxRate(countryId: number) {
    const ok = await this.confirmDialog.open({
      title: 'Eliminar tasa de IVA',
      message: '¿Eliminar esta tasa de IVA?',
      confirmLabel: 'Eliminar',
      variant: 'danger',
    });
    if (!ok) return;
    this.api
      .deleteTaxRate(countryId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.taxRatesResource.reload(),
        error: () => {
          this.taxMessage.set('Error al eliminar la tasa de IVA');
        },
      });
  }

  // ─── Commission Rates ──────────────────────────────────────────

  addCommissionRate() {
    const propId = this.newCommissionPropId();
    if (propId === null) return;
    this.commissionSaving.set(true);
    this.commissionMessage.set('');
    this.api
      .createCommissionRate({ prop_id: propId, commission_pct: this.newCommissionPct() })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.commissionSaving.set(false);
          this.newCommissionPropId.set(null);
          this.newCommissionPct.set(5.0);
          this.commissionRatesResource.reload();
        },
        error: () => {
          this.commissionSaving.set(false);
          this.commissionMessage.set('Error al crear la comisión');
        },
      });
  }

  startEditCommission(rate: CommissionRate) {
    this.editingCommission.set(rate.propId);
    this.editCommissionPct.set(rate.commissionPct);
    this.commissionMessage.set('');
  }

  cancelEditCommission() {
    this.editingCommission.set(null);
  }

  saveCommissionRate(propId: number) {
    this.commissionSaving.set(true);
    this.commissionMessage.set('');
    this.api
      .updateCommissionRate(propId, { commission_pct: this.editCommissionPct() })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.commissionSaving.set(false);
          this.editingCommission.set(null);
          this.commissionRatesResource.reload();
        },
        error: () => {
          this.commissionSaving.set(false);
          this.commissionMessage.set('Error al actualizar la comisión');
        },
      });
  }

  async deleteCommissionRate(propId: number) {
    const ok = await this.confirmDialog.open({
      title: 'Eliminar comisión',
      message: '¿Eliminar esta comisión?',
      confirmLabel: 'Eliminar',
      variant: 'danger',
    });
    if (!ok) return;
    this.api
      .deleteCommissionRate(propId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.commissionRatesResource.reload(),
        error: () => {
          this.commissionMessage.set('Error al eliminar la comisión');
        },
      });
  }
}
