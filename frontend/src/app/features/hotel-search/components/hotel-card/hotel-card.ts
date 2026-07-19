import { Component, computed, DestroyRef, inject, input, OnInit, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { TrackingService } from '../../../../core/tracking/tracking.service';
import type { HotelSearchResult } from '../../models/hotel-search.model';

@Component({
  selector: 'app-hotel-card',
  imports: [RouterLink],
  templateUrl: './hotel-card.html',
  styleUrl: './hotel-card.scss'
})
export class HotelCardComponent implements OnInit {
  private readonly tracking = inject(TrackingService);
  private readonly destroyRef = inject(DestroyRef);

  readonly hotel = input.required<HotelSearchResult>();
  readonly compareMode = input(false);
  readonly compareSelected = output<number>();

  readonly fallbackImg = signal(false);
  readonly currentImageIdx = signal(0);
  readonly noTransition = signal(false);
  private rotationTimer: ReturnType<typeof setInterval> | null = null;
  readonly totalImages = 3;

  ngOnInit() {
    this.destroyRef.onDestroy(() => {
      if (this.rotationTimer) clearInterval(this.rotationTimer);
    });
  }

  readonly galleryImages = computed(() => {
    const h = this.hotel();
    if (this.fallbackImg()) return [];
    return [
      `https://loremflickr.com/400/250/hotel?lock=${h.id}1`,
      `https://loremflickr.com/400/250/hotel,lobby?lock=${h.id}2`,
      `https://loremflickr.com/400/250/hotel,pool?lock=${h.id}3`
    ];
  });

  readonly imageUrl = computed(() => {
    const h = this.hotel();
    if (h.imageUrl && !this.fallbackImg()) return h.imageUrl;
    const gallery = this.galleryImages();
    return gallery.length ? gallery[0] : `https://loremflickr.com/400/250/hotel?lock=${h.id}1`;
  });

  /** TranslateX offset for the carousel strip — slides to the active image. */
  readonly stripOffset = computed(() => {
    if (this.fallbackImg()) return '';
    return `translateX(-${this.currentImageIdx() * 100}%)`;
  });

  startRotation() {
    if (this.fallbackImg() || this.rotationTimer) return;
    this.rotationTimer = setInterval(() => {
      const next = (this.currentImageIdx() + 1) % this.totalImages;
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
    const destinations = h.destinationLabels.length
      ? `Ideal para ${h.destinationLabels.slice(0, 2).join(' y ')}.`
      : 'Disponible para estancias urbanas y escapadas de viaje.';
    const review = h.reviewScore ? `Puntuación ${h.reviewScore.toFixed(1)}/10. ` : '';
    const rooms = h.availableRoomTypesCount ? `${h.availableRoomTypesCount} tipo(s) de habitación disponible(s). ` : '';
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
}
