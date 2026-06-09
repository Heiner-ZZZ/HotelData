import { Component, input } from '@angular/core';

@Component({
  selector: 'app-status-badge',
  templateUrl: './status-badge.html',
  styleUrl: './status-badge.scss'
})
export class StatusBadgeComponent {
  readonly tone = input<'neutral' | 'success' | 'warning' | 'danger'>('neutral');
  readonly label = input.required<string>();
}
