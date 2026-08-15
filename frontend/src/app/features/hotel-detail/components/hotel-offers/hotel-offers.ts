import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';

import type { HotelOffersDto } from '../../models/hotel-detail.dto';

/**
 * Sección pública «Ofertas y promociones» de la página del hotel.
 *
 * Consume `GET /api/hotels/{prop_id}/promotions` (público, sin auth): las
 * campañas promocionales que el hotel ha enviado, más recientes primero.
 * El backend nunca expone el `message` (PII) — aquí solo título + fecha.
 * Sin ofertas activas, el componente no renderiza nada (la sección
 * desaparece de la página).
 */
@Component({
  selector: 'app-hotel-offers',
  imports: [DatePipe],
  templateUrl: './hotel-offers.html',
  styleUrl: './hotel-offers.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HotelOffersComponent {
  /** Id del hotel (prop_id) cuyas ofertas activas se muestran. */
  readonly propId = input.required<number>();

  readonly offersResource = httpResource<HotelOffersDto>(() => {
    const id = this.propId();
    return id > 0 ? `/api/hotels/${id}/promotions` : undefined;
  });

  readonly offers = computed(() => this.offersResource.value()?.items ?? []);
}
