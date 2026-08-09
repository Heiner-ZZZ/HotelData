import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, input, OnInit, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { FavoritesService } from '../../../../core/favorites/favorites.service';
import { toast } from '../../../../core/toast/toast.service';
import { TrackingService } from '../../../../core/tracking/tracking.service';
import {
  isValidImageUrl,
  placeholderImageUrl,
} from '../../../../shared/utils/placeholder-image.util';
import type { HotelSearchResult } from '../../models/hotel-search.model';

@Component({
  selector: 'app-hotel-card',
  imports: [RouterLink],
  templateUrl: './hotel-card.html',
  styleUrl: './hotel-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelCardComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly favorites = inject(FavoritesService);
  private readonly tracking = inject(TrackingService);
  private readonly destroyRef = inject(DestroyRef);

  readonly hotel = input.required<HotelSearchResult>();
  readonly compareMode = input(false);
  readonly compareSelected = output<number>();
  /** Solo la página de búsqueda habilita el botón Elegir fechas (tiene el
   *  filtro con el calendario a la vista); favoritos/similares lo omiten. */
  readonly chooseDatesEnabled = input(false);
  readonly chooseDates = output<void>();
  /** Rango elegido en la búsqueda — la card calcula el total (base × noches)
   *  de forma reactiva; el total_estimated del backend manda cuando llega. */
  readonly checkIn = input('');
  readonly checkOut = input('');

  /** Favorite state — O(1) lookup via direct Set membership. */
  readonly isFavorited = computed(() => this.favorites.favoriteIds().has(this.hotel().id));

  readonly currentImageIdx = signal(0);
  readonly noTransition = signal(false);
  /** URLs cuya carga falló — se filtran de la galería sin colapsarla. */
  private readonly failedImageSrcs = signal<Set<string>>(new Set());
  private rotationTimer: ReturnType<typeof setInterval> | null = null;

  readonly BASE_GALLERY_COUNT = 3;

  /**
   * Request-free gallery for search cards: the availability endpoint already
   * includes the first hotel image, and deterministic loremflickr placeholders
   * (seeded by hotel id) fill the rest so every card has a navigable carousel
   * (arrows + dots) without extra API calls. Detail pages remain the place
   * for the full gallery.
   */
  readonly galleryImages = computed(() => {
    const h = this.hotel();
    const failed = this.failedImageSrcs();
    const primaryImage = h.imageUrl && isValidImageUrl(h.imageUrl) ? [h.imageUrl] : [];
    return [
      ...primaryImage,
      placeholderImageUrl(`${h.id}1`),
      placeholderImageUrl(`${h.id}2`),
      placeholderImageUrl(`${h.id}3`),
    ].filter((url) => !failed.has(this.resolveUrl(url)));
  });

  /** Noches entre check-in y check-out (null si el rango es inválido o vacío). */
  readonly nights = computed<number | null>(() => {
    const from = this.checkIn();
    const to = this.checkOut();
    if (!from || !to) return null;
    const start = new Date(from);
    const end = new Date(to);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;
    const diff = Math.round((end.getTime() - start.getTime()) / 86_400_000);
    return diff >= 1 ? diff : null;
  });

  /** Total a mostrar: el total_estimated del backend manda; si no llega (o la
   *  búsqueda no trajo fechas), se calcula localmente = precio base × noches. */
  readonly displayTotal = computed<number | null>(() => {
    const fromBackend = this.hotel().totalEstimated;
    if (fromBackend !== null && fromBackend !== undefined) return fromBackend;
    const rate = this.hotel().minNightlyRate;
    const nights = this.nights();
    if (rate === null || rate === undefined || nights === null) return null;
    return Math.round(rate * nights * 100) / 100;
  });

  readonly displayTotalLabel = computed<string | null>(() => {
    const total = this.displayTotal();
    if (total === null) return null;
    const fromBackend = this.hotel().totalEstimatedLabel;
    if (this.hotel().totalEstimated !== null && this.hotel().totalEstimated !== undefined && fromBackend) {
      return fromBackend;
    }
    return `S/ ${total.toFixed(2)}`;
  });

  /** Línea de disponibilidad: cuántas quedan a ese precio (solo con fechas). */
  readonly availableRoomsLabel = computed<string | null>(() => {
    const remaining = this.hotel().minAvailableRooms;
    if (remaining === null || remaining === undefined || remaining < 1) return null;
    return remaining === 1 ? 'Queda 1 a este precio' : `Quedan ${remaining} a este precio`;
  });

  /** Patrón Expedia: sin fechas no hay total ni cantidad → se invita a
   *  elegir fechas primero (botón encima de Ver disponibilidad). */
  readonly showChooseDates = computed(
    () => this.chooseDatesEnabled() && !this.displayTotalLabel() && !this.availableRoomsLabel(),
  );

  /** Total images in the carousel — dynamic based on gallery. */
  readonly totalImages = computed(() => this.galleryImages().length);

  /** Generate dot indices for the carousel indicators. */
  readonly dotIndices = computed(() => {
    const count = this.totalImages();
    if (count <= 1) return [0] as const;
    if (count <= this.BASE_GALLERY_COUNT) return [0, 1, 2] as const;
    return Array.from({ length: count }, (_, i) => i);
  });

  ngOnInit() {
    this.destroyRef.onDestroy(() => {
      if (this.rotationTimer) clearInterval(this.rotationTimer);
    });
  }

  readonly imageUrl = computed(() => {
    const h = this.hotel();
    const gallery = this.galleryImages();
    return gallery.length ? gallery[0] : placeholderImageUrl(`${h.id}1`);
  });

  /** TranslateX offset for the carousel strip — slides to the active image. */
  readonly stripOffset = computed(() => {
    if (this.totalImages() <= 1) return '';
    return `translateX(-${this.currentImageIdx() * 100}%)`;
  });

  startRotation() {
    if (this.rotationTimer || this.totalImages() <= 1) return;
    this.rotationTimer = setInterval(() => {
      const next = (this.currentImageIdx() + 1) % this.totalImages();
      if (next === 0) {
        this.noTransition.set(true);
        this.currentImageIdx.set(0);
        setTimeout(() => this.noTransition.set(false), 50);
      } else {
        this.currentImageIdx.set(next);
      }
    }, 3500);
  }

  stopRotation() {
    if (this.rotationTimer) {
      clearInterval(this.rotationTimer);
      this.rotationTimer = null;
    }
    this.currentImageIdx.set(0);
    this.noTransition.set(false);
  }

  goToImage(idx: number) {
    this.currentImageIdx.set(idx);
  }

  prevImage() {
    this.stepImage(-1);
  }

  nextImage() {
    this.stepImage(1);
  }

  /** Step the carousel with wrap-around and restart auto-rotation from the new index. */
  private stepImage(dir: 1 | -1) {
    const total = this.totalImages();
    if (total <= 1) return;
    this.currentImageIdx.set((this.currentImageIdx() + dir + total) % total);
    if (this.rotationTimer) {
      clearInterval(this.rotationTimer);
      this.rotationTimer = null;
      this.startRotation();
    }
  }

  /** Normaliza URLs (relativas → absolutas) para comparar src de <img> con la galería. */
  private resolveUrl(url: string): string {
    try {
      return new URL(url, window.location.origin).href;
    } catch {
      return url;
    }
  }

  /** Una imagen que falla se quita de la galería; el resto (y sus flechas/puntitos) siguen. */
  onImgError(img: HTMLImageElement | null) {
    const src = img?.currentSrc || img?.src || '';
    if (!src) return;
    this.failedImageSrcs.update((failed) => new Set(failed).add(this.resolveUrl(src)));
  }

  readonly imageThemes = [
    'theme-amber',
    'theme-ocean',
    'theme-forest',
    'theme-rose'
  ];

  get imageTheme(): string {
    return this.imageThemes[this.hotel().id % this.imageThemes.length];
  }

  get headlineMeta(): string {
    const starsValue = this.hotel().stars;
    return typeof starsValue === 'number' ? `${starsValue.toFixed(1)} estrellas` : 'Categoría por confirmar';
  }

  get scoreLabel(): string {
    const score = this.hotel().reviewScore;
    if (score !== null && score !== undefined && Number.isFinite(score)) {
      return score.toFixed(1);
    }
    const stars = this.hotel().stars;
    if (typeof stars === 'number' && stars >= 4.5) return '9.0';
    if (typeof stars === 'number' && stars >= 4) return '8.7';
    if (typeof stars === 'number' && stars >= 3) return '8.0';
    return '7.5';
  }

  get scoreTitle(): string {
    const score = this.hotel().reviewScore;
    if (score !== null && score !== undefined && Number.isFinite(score)) {
      if (score >= 9) return 'Excepcional';
      if (score >= 8) return 'Fabuloso';
      if (score >= 7) return 'Muy bueno';
      return 'Bueno';
    }
    const stars = this.hotel().stars;
    if (typeof stars === 'number' && stars >= 4.5) return 'Excepcional';
    if (typeof stars === 'number' && stars >= 4) return 'Fabuloso';
    return 'Muy bueno';
  }

  get roomTypeLabel(): string {
    const rt = this.hotel().matchedRoomType;
    if (!rt) return '';
    return `${rt.name} · ${rt.maxAdults} adulto${rt.maxAdults !== 1 ? 's' : ''} · ${rt.baseCapacity} capacidad`;
  }

  trackClick(): void {
    this.tracking.trackHotelClick(this.hotel().id, 'search');
  }

  toggleCompare(): void {
    this.compareSelected.emit(this.hotel().id);
  }

  toggleFav(event: Event): void {
    event.preventDefault();
    event.stopPropagation();

    if (!this.auth.isAuthenticated()) {
      toast('Inicia sesión para guardar hoteles favoritos', 'info', 3000);
      return;
    }

    this.favorites.toggle(this.hotel().id);
  }
}
