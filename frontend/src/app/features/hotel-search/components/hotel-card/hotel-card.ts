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

  /** Favorite state — O(1) lookup via direct Set membership. */
  readonly isFavorited = computed(() => this.favorites.favoriteIds().has(this.hotel().id));

  readonly fallbackImg = signal(false);
  readonly currentImageIdx = signal(0);
  readonly noTransition = signal(false);
  private rotationTimer: ReturnType<typeof setInterval> | null = null;

  readonly BASE_GALLERY_COUNT = 3;

  /**
   * Small, request-free gallery for search cards. The availability endpoint
   * already includes the first hotel image, so fetching hotel, amenity and
   * room images for every card would turn a 10-result page into 30 extra
   * requests. Detail pages remain the place for the full gallery.
   */
  readonly galleryImages = computed(() => {
    const h = this.hotel();
    if (this.fallbackImg()) return [];
    const primaryImage = h.imageUrl && isValidImageUrl(h.imageUrl) ? [h.imageUrl] : [];
    return primaryImage;
  });

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
    if (h.imageUrl && !this.fallbackImg()) return h.imageUrl;
    const gallery = this.galleryImages();
    return gallery.length ? gallery[0] : placeholderImageUrl(`${h.id}1`);
  });

  /** TranslateX offset for the carousel strip — slides to the active image. */
  readonly stripOffset = computed(() => {
    if (this.fallbackImg()) return '';
    return `translateX(-${this.currentImageIdx() * 100}%)`;
  });

  startRotation() {
    if (this.fallbackImg() || this.rotationTimer || this.totalImages() <= 1) return;
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

  onImgError() {
    this.fallbackImg.set(true);
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

  get summaryText(): string {
    const h = this.hotel();
    // No defensive `?? []` here. The mapper is the single canonical audit
    // point — if `destinationLabels` ever arrives undefined, the mapper
    // already rejected that item and toasts a wire-shape regression in dev.
    // Trusting the canonical type lets a real backend bug crash loudly
    // instead of being masked by a silent fallback that misleads the user
    // with the generic "Disponible para estancias urbanas…" copy.
    const labels = h.destinationLabels;
    const destinations = labels.length > 0
      ? `Ideal para ${labels.slice(0, 2).join(' y ')}.`
      : 'Disponible para estancias urbanas y escapadas de viaje.';
    const review = h.reviewScore != null
      ? `Puntuación ${h.reviewScore.toFixed(1)}/10. `
      : '';
    const rooms = h.availableRoomTypesCount
      ? `${h.availableRoomTypesCount} tipo(s) de habitación disponible(s). `
      : '';
    return `${review}${rooms}${destinations}`;
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
