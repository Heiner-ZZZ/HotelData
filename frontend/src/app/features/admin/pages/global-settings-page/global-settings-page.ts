import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
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
import { GlobalSettingsApiService } from '../../services/global-settings-api.service';

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
  private readonly destroyRef = inject(DestroyRef);

  readonly activeTab = signal<ActiveTab>('hotels');

  // Platform Config
  readonly configState = signal<ViewState>('loading');
  readonly config = signal<PlatformConfig | null>(null);
  readonly editCommission = signal(5.0);
  readonly editIva = signal(16.0);
  readonly configSaving = signal(false);
  readonly configMessage = signal('');

  // Hotels
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
  readonly taxState = signal<ViewState>('loading');
  readonly taxRates = signal<TaxRate[]>([]);
  readonly newTaxCountryId = signal<number | null>(null);
  readonly newTaxCountryName = signal('');
  readonly newTaxIva = signal(16.0);
  readonly editingTax = signal<number | null>(null);
  readonly editTaxIva = signal(16.0);
  readonly taxSaving = signal(false);
  readonly taxMessage = signal('');

  // Commission Rates
  readonly commissionState = signal<ViewState>('loading');
  readonly commissionRates = signal<CommissionRate[]>([]);
  readonly newCommissionPropId = signal<number | null>(null);
  readonly newCommissionPct = signal(5.0);
  readonly editingCommission = signal<number | null>(null);
  readonly editCommissionPct = signal(5.0);
  readonly commissionSaving = signal(false);
  readonly commissionMessage = signal('');

  constructor() {
    this.loadConfig();
    this.loadHotels();
    this.loadTaxRates();
    this.loadCommissionRates();
  }

  setTab(tab: ActiveTab) {
    this.activeTab.set(tab);
  }

  // ─── Config ────────────────────────────────────────────────────

  private loadConfig() {
    this.configState.set('loading');
    this.api.getConfig().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (cfg) => {
        this.config.set(cfg);
        this.editCommission.set(cfg.defaultCommissionPct);
        this.editIva.set(cfg.defaultIvaPct);
        this.configState.set('success');
      },
      error: () => {
        this.configState.set('error');
      },
    });
  }

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
          this.config.set(cfg);
          this.configSaving.set(false);
          this.configMessage.set('Configuración guardada correctamente');
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

  loadTaxRates() {
    this.taxState.set('loading');
    this.api
      .listTaxRates()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (rates) => {
          this.taxRates.set(rates);
          this.taxState.set(rates.length ? 'success' : 'empty');
        },
        error: () => {
          this.taxState.set('error');
        },
      });
  }

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
          this.loadTaxRates();
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
          this.loadTaxRates();
        },
        error: () => {
          this.taxSaving.set(false);
          this.taxMessage.set('Error al actualizar la tasa de IVA');
        },
      });
  }

  deleteTaxRate(countryId: number) {
    if (!confirm('¿Eliminar esta tasa de IVA?')) return;
    this.api
      .deleteTaxRate(countryId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.loadTaxRates(),
        error: () => {
          this.taxMessage.set('Error al eliminar la tasa de IVA');
        },
      });
  }

  // ─── Commission Rates ──────────────────────────────────────────

  loadCommissionRates() {
    this.commissionState.set('loading');
    this.api
      .listCommissionRates()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (rates) => {
          this.commissionRates.set(rates);
          this.commissionState.set(rates.length ? 'success' : 'empty');
        },
        error: () => {
          this.commissionState.set('error');
        },
      });
  }

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
          this.loadCommissionRates();
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
          this.loadCommissionRates();
        },
        error: () => {
          this.commissionSaving.set(false);
          this.commissionMessage.set('Error al actualizar la comisión');
        },
      });
  }

  deleteCommissionRate(propId: number) {
    if (!confirm('¿Eliminar esta comisión?')) return;
    this.api
      .deleteCommissionRate(propId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.loadCommissionRates(),
        error: () => {
          this.commissionMessage.set('Error al eliminar la comisión');
        },
      });
  }
}
