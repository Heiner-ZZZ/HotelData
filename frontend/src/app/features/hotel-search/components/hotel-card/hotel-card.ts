import { Component, computed, input, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import type { HotelSearchResult } from '../../models/hotel-search.model';

@Component({
  selector: 'app-hotel-card',
  imports: [RouterLink],
  templateUrl: './hotel-card.html',
  styleUrl: './hotel-card.scss'
})
export class HotelCardComponent {
  readonly hotel = input.required<HotelSearchResult>();
  readonly compareMode = input(false);
  readonly compareSelected = output<number>();

  readonly imgError = signal(false);

  readonly picsumUrl = computed(() =>
    `https://picsum.photos/seed/${this.hotel().id}/400/250`
  );

  onImgError() {
    this.imgError.set(true);
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
    return `ID ${this.hotel().id} · ${stars}`;
  }

  get summaryText(): string {
    const destinations = this.hotel().destinationLabels.length
      ? `Ideal para ${this.hotel().destinationLabels.slice(0, 2).join(' y ')}.`
      : 'Disponible para estancias urbanas y escapadas de viaje.';
    return `${this.hotel().name}. ${destinations}`;
  }

  get scoreLabel(): string {
    const score = this.hotel().reviewScore;
    if (score !== null && score !== undefined && Number.isFinite(score)) {
      return score.toFixed(1);
    }
    const stars = this.hotel().stars;
    if (typeof stars === 'number' && stars >= 4.5) return '9.0';
    if (typeof stars === 'number' && stars >= 4) return '8.7';
    return '8.2';
  }

  get scoreTitle(): string {
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

  toggleCompare(): void {
    this.compareSelected.emit(this.hotel().id);
  }
}
