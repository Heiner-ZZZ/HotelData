import { Component, input } from '@angular/core';

import type { RateCalendarItem } from '../../models/rates.model';

@Component({
  selector: 'app-rate-calendar-table',
  templateUrl: './rate-calendar-table.html',
  styleUrl: './rate-calendar-table.scss'
})
export class RateCalendarTableComponent {
  readonly items = input<RateCalendarItem[]>([]);
}
