import { Component, input } from '@angular/core';

@Component({
  selector: 'app-property-facts-panel',
  templateUrl: './property-facts-panel.html',
  styleUrl: './property-facts-panel.scss'
})
export class PropertyFactsPanelComponent {
  readonly title = input.required<string>();
  readonly facts = input<{ label: string; value: string }[]>([]);
}
