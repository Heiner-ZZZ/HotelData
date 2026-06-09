import { Component, input } from '@angular/core';
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
    return `${this.hotel().location} · ${stars}`;
  }

  get reviewSummary(): string {
    return `${this.hotel().reservations} reservas · ${this.hotel().clicks} interacciones`;
  }

  get summaryText(): string {
    const destinations = this.hotel().destinationLabels.length
      ? `Ideal para ${this.hotel().destinationLabels.slice(0, 2).join(' y ')}.`
      : 'Disponible para estancias urbanas y escapadas de viaje.';
    const promotion = this.hotel().hasPromotion ? 'Incluye una promoción activa ahora mismo.' : 'Tarifa disponible para consulta inmediata.';
    return `${this.hotel().name} ofrece una experiencia bien posicionada en ${this.hotel().location}. ${destinations} ${promotion}`;
  }

  get scoreLabel(): string {
    const stars = this.hotel().stars;
    const score = Number(this.hotel().reviewLabel);
    if (!Number.isNaN(score) && Number.isFinite(score)) {
      return score.toFixed(1);
    }

    if (typeof stars === 'number' && stars >= 4.5) {
      return '9.0';
    }
    if (typeof stars === 'number' && stars >= 4) {
      return '8.7';
    }
    return '8.2';
  }

  get scoreTitle(): string {
    const stars = this.hotel().stars;
    if (typeof stars === 'number' && stars >= 4.5) {
      return 'Excepcional';
    }
    if (typeof stars === 'number' && stars >= 4) {
      return 'Fabuloso';
    }
    return 'Muy bueno';
  }
}
