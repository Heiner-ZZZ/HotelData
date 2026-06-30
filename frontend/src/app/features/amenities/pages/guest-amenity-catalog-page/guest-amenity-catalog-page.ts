import { CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { GuestAmenityService } from '../../services/guest-amenity.service';
import type { GuestAmenityCategoryDto, GuestAmenityItemDto, GuestAmenityRequestItem, GuestAmenityRequestResponseDto } from '../../models/guest-amenity.dto';
import type { ViewState } from '../../../../shared/types/ui-state.type';

/** Icons per amenity category for visual distinction. */
const CATEGORY_ICONS: Record<string, string> = {
  desayuno: 'free_breakfast',
  alimentos: 'restaurant',
  bebidas: 'local_bar',
  spa: 'spa',
  bienestar: 'self_improvement',
  habitación: 'bed',
  habitacion: 'bed',
  entretenimiento: 'tv',
  transporte: 'directions_car',
  servicios: 'room_service',
  lavandería: 'local_laundry_service',
  lavanderia: 'local_laundry_service',
  limpieza: 'cleaning_services',
  mascotas: 'pets',
  tecnología: 'devices',
  tecnologia: 'devices',
  gimnasio: 'fitness_center',
  piscina: 'pool',
  playa: 'beach_access',
  tour: 'explore',
  excursión: 'hiking',
  excursion: 'hiking',
  parking: 'local_parking',
  wifi: 'wifi',
  default: 'stars',
};

function categoryIcon(category: string): string {
  const key = category.toLowerCase().trim();
  return CATEGORY_ICONS[key] || CATEGORY_ICONS['default'];
}

@Component({
  selector: 'app-guest-amenity-catalog-page',
  imports: [CurrencyPipe, EmptyStateComponent, ErrorStateComponent, FormsModule, LoadingStateComponent],
  templateUrl: './guest-amenity-catalog-page.html',
  styleUrl: './guest-amenity-catalog-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GuestAmenityCatalogPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly guestAmenityService = inject(GuestAmenityService);
  private readonly router = inject(Router);

  readonly categoryIcon = categoryIcon;

  // ── Core state ──
  readonly bookingId = signal('');
  readonly viewState = signal<ViewState>('loading');
  readonly catalog = signal<GuestAmenityCategoryDto[]>([]);
  readonly bookingInfo = signal<{ guest_name: string; check_in: string; check_out: string; hotel_label: string } | null>(null);
  readonly errorMessage = signal('');

  // ── Search & filter ──
  readonly searchQuery = signal('');
  readonly showPaidOnly = signal(false);
  readonly selectedCategory = signal<string | null>(null);

  /** Unique category names extracted from the catalog. */
  readonly categories = computed<string[]>(() => {
    return this.catalog().map((c) => c.category);
  });

  /** Catalog filtered by search query, paid-only toggle, and category. */
  readonly filteredCatalog = computed(() => {
    const cat = this.catalog();
    const query = this.searchQuery().toLowerCase().trim();
    const paidOnly = this.showPaidOnly();
    const category = this.selectedCategory();

    return cat
      .filter((c) => !category || c.category === category)
      .map((c) => ({
        ...c,
        items: c.items.filter((item) => {
          if (paidOnly && item.unit_price <= 0) return false;
          if (query && !item.label.toLowerCase().includes(query)) return false;
          return true;
        }),
      }))
      .filter((c) => c.items.length > 0);
  });

  /** Whether the filtered catalog result is empty despite having a full catalog. */
  readonly hasFilterMatch = computed(() => {
    if (!this.searchQuery() && !this.showPaidOnly() && !this.selectedCategory()) return true;
    return this.filteredCatalog().length > 0;
  });

  /** Total items matching current filter (across all categories). */
  readonly filteredItemCount = computed(() => {
    return this.filteredCatalog().reduce((sum, c) => sum + c.items.length, 0);
  });

  selectCategory(category: string | null) {
    this.selectedCategory.set(category);
  }

  // ── Collapsible categories ──
  readonly collapsedCategories = signal<Set<string>>(new Set());

  toggleCategory(category: string) {
    const s = new Set(this.collapsedCategories());
    if (s.has(category)) s.delete(category);
    else s.add(category);
    this.collapsedCategories.set(s);
  }

  isCategoryCollapsed(category: string): boolean {
    return this.collapsedCategories().has(category);
  }

  // ── Cart state ──
  readonly cart = signal<Map<string, number>>(new Map());
  readonly requesting = signal(false);
  readonly requestResult = signal<GuestAmenityRequestResponseDto | null>(null);
  readonly showCartDrawer = signal(false);

  readonly cartEntries = computed(() => {
    const c = this.cart();
    return [...c.entries()].filter(([, qty]) => qty > 0);
  });

  readonly cartTotal = computed(() => {
    const cat = this.catalog();
    const c = this.cart();
    let total = 0;
    for (const [label, qty] of c) {
      const price = this._findPrice(label, cat);
      if (price > 0) total += price * qty;
    }
    return total;
  });

  readonly cartFreeCount = computed(() => {
    const cat = this.catalog();
    const c = this.cart();
    let count = 0;
    for (const [label, qty] of c) {
      const price = this._findPrice(label, cat);
      if (price <= 0) count += qty;
    }
    return count;
  });

  readonly cartPaidCount = computed(() => {
    return this.cartCount() - this.cartFreeCount();
  });

  readonly cartCount = computed(() => {
    return this.cartEntries().reduce((sum, [, qty]) => sum + qty, 0);
  });

  /** Enriched cart entries with price, stock info per item. */
  readonly cartDetails = computed(() => {
    const cat = this.catalog();
    return this.cartEntries().map(([label, qty]) => {
      const price = this._findPrice(label, cat);
      const stock = this._findStock(label, cat);
      return { label, qty, unitPrice: price, total: price * qty, free: price <= 0, stock };
    });
  });

  // ── Lifecycle ──
  constructor() {
    this.activatedRoute.paramMap
      .pipe(
        map((params) => params.get('bookingId') ?? ''),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((bookingId) => {
        if (!bookingId) {
          this.viewState.set('empty');
          return;
        }
        this.bookingId.set(bookingId);
        this._loadCatalog(bookingId);
      });
  }

  private _loadCatalog(bookingId: string) {
    this.viewState.set('loading');
    this.guestAmenityService.getCatalog(bookingId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (dto) => {
        this.catalog.set(dto.catalog);
        this.bookingInfo.set({
          guest_name: dto.booking.guest_name,
          check_in: dto.booking.check_in,
          check_out: dto.booking.check_out,
          hotel_label: dto.booking.hotel_label || 'Hotel',
        });
        this.viewState.set('success');
      },
      error: (err: ApiError) => {
        this.errorMessage.set(err.message || 'No se pudo cargar el catálogo de amenities.');
        this.viewState.set('error');
      },
    });
  }

  private _findPrice(label: string, catalog: GuestAmenityCategoryDto[]): number {
    for (const cat of catalog) {
      for (const item of cat.items) {
        if (item.label === label) return item.unit_price;
      }
    }
    return 0;
  }

  private _findStock(label: string, catalog: GuestAmenityCategoryDto[]): number | undefined {
    for (const cat of catalog) {
      for (const item of cat.items) {
        if (item.label === label) return item.available_stock;
      }
    }
    return undefined;
  }

  private _findItem(label: string, catalog: GuestAmenityCategoryDto[]): GuestAmenityItemDto | undefined {
    for (const cat of catalog) {
      for (const item of cat.items) {
        if (item.label === label) return item;
      }
    }
    return undefined;
  }

  // ── Stock helpers ──

  getStock(item: GuestAmenityItemDto): number | '∞' {
    return item.available_stock ?? '∞';
  }

  isOutOfStock(item: GuestAmenityItemDto): boolean {
    return item.available_stock !== null && item.available_stock !== undefined && item.available_stock <= 0;
  }

  /** Whether stock is low (≤3 remaining) for visual warning. */
  isLowStock(item: GuestAmenityItemDto): boolean {
    const s = item.available_stock;
    return s !== null && s !== undefined && s <= 3;
  }

  /** Stock ratio (0-1) for visual progress bar. 1 = full stock, 0 = out. */
  stockRatio(item: GuestAmenityItemDto): number {
    const s = item.available_stock;
    if (s === null || s === undefined) return 1; // unlimited
    if (s <= 0) return 0;
    // Cap display at 20 units for the bar
    return Math.min(s / 20, 1);
  }

  stockBarColor(ratio: number): string {
    if (ratio <= 0.15) return '#ef4444';   // red
    if (ratio <= 0.35) return '#f59e0b';   // amber
    return '#16a34a';                        // green
  }

  /** Max quantity the guest can add based on stock. */
  maxQtyFor(label: string): number {
    const cat = this.catalog();
    const item = this._findItem(label, cat);
    if (!item) return 99;
    if (item.available_stock === null || item.available_stock === undefined) return 99;
    return item.available_stock;
  }

  // ── Cart actions ──

  addToCart(label: string) {
    const max = this.maxQtyFor(label);
    const c = new Map(this.cart());
    const current = c.get(label) || 0;
    if (current >= max) return; // at stock limit
    c.set(label, current + 1);
    this.cart.set(c);
  }

  removeFromCart(label: string) {
    const c = new Map(this.cart());
    const current = c.get(label) || 0;
    if (current <= 1) {
      c.delete(label);
    } else {
      c.set(label, current - 1);
    }
    this.cart.set(c);
  }

  setCartQty(label: string, qty: number) {
    const max = this.maxQtyFor(label);
    const clamped = Math.max(0, Math.min(qty, max));
    const c = new Map(this.cart());
    if (clamped <= 0) {
      c.delete(label);
    } else {
      c.set(label, clamped);
    }
    this.cart.set(c);
  }

  clearCart() {
    this.cart.set(new Map());
    this.showCartDrawer.set(false);
  }

  getCartQty(label: string): number {
    return this.cart().get(label) || 0;
  }

  toggleCartDrawer() {
    this.showCartDrawer.set(!this.showCartDrawer());
  }

  // ── Submit ──

  submitRequest() {
    const entries = this.cartEntries();
    if (entries.length === 0) return;

    this.requesting.set(true);
    this.errorMessage.set('');

    const items: GuestAmenityRequestItem[] = entries.map(([label, quantity]) => ({ label, quantity }));
    const bookingId = this.bookingId();

    this.guestAmenityService.requestAmenities({ booking_id: bookingId, items })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.requestResult.set(result);
          this.requesting.set(false);
          if (result.ok) {
            this.clearCart();
            this.showCartDrawer.set(false);
          }
        },
        error: (err: ApiError) => {
          this.errorMessage.set(err.message || 'Error al solicitar amenities.');
          this.requesting.set(false);
        },
      });
  }

  // ── Navigation ──

  goBack() {
    this.router.navigate(['/account/bookings', this.bookingId()]);
  }

  dismissResult() {
    this.requestResult.set(null);
  }

  setSearchQuery(value: string) {
    this.searchQuery.set(value);
  }

  togglePaidOnly() {
    this.showPaidOnly.set(!this.showPaidOnly());
  }
}
