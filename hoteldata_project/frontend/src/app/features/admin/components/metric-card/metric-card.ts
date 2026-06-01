import { Component, input } from '@angular/core';

@Component({
  selector: 'app-metric-card',
  templateUrl: './metric-card.html',
  styleUrl: './metric-card.scss'
})
export class MetricCardComponent {
  readonly label = input.required<string>();
  readonly value = input.required<string>();
  readonly detail = input('');
  readonly trend = input('');
  readonly direction = input<'up' | 'down'>('up');
}
