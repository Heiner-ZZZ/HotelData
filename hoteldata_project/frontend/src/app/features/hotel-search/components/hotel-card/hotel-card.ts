import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { HotelSearchResult } from '../../models/hotel-search.model';

@Component({
  selector: 'app-hotel-card',
  imports: [RouterLink, StatusBadgeComponent],
  templateUrl: './hotel-card.html',
  styleUrl: './hotel-card.scss'
})
export class HotelCardComponent {
  readonly hotel = input.required<HotelSearchResult>();
}
