import { Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  templateUrl: './empty-state.html',
  styleUrl: './empty-state.scss'
})
export class EmptyStateComponent {
  readonly title = input.required<string>();
  readonly description = input('');
}
