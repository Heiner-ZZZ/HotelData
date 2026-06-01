import { Component, input } from '@angular/core';

@Component({
  selector: 'app-occupancy-summary',
  templateUrl: './occupancy-summary.html',
  styleUrl: './occupancy-summary.scss'
})
export class OccupancySummaryComponent {
  readonly items = input<Array<{ label: string; value: string }>>([]);
}
