import { Component, computed, inject, input, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { TrackingService } from '../../../../core/tracking/tracking.service';
import type { HotelSearchResult } from '../../models/hotel-search.model';

@Component({
  selector: 'app-hotel-card',
  imports: [RouterLink],
  templateUrl: './hotel-card.html',
  styleUrl: './hotel-card.scss'
})
export class HotelCardComponent {
  private readonly tracking = inject(TrackingService);

  readonly hotel = input.required<HotelSearchResult>();
  readonly compareMode = input(false);
  readonly compareSelected = output<number>();

  readonly fallbackImg = signal(false);

  readonly imageUrl = computed(() => {
    const h = this.hotel();
    if (h.imageUrl && !this.fallbackImg()) return h.imageUrl;
    return `https://loremflickr.com/400/250/hotel?lock=${h.id}1`;
  });

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
    const stars = typeof starsValue === 'number' ? `${starsValue.toFixed(1)} estrellas` : 'Categoría por confirmar';
    return `Hotel #${this.hotel().id} · ${stars}`;
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
