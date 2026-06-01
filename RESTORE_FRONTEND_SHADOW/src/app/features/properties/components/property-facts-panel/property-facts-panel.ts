import { Component, input } from '@angular/core';

@Component({
  selector: 'app-property-facts-panel',
  standalone: true,
  templateUrl: './property-facts-panel.html',
  styleUrl: './property-facts-panel.scss'
})
export class PropertyFactsPanelComponent {
  readonly title = input.required<string>();
  readonly facts = input<Array<{ label: string; value: string }>>([]);
}
