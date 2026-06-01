import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import type { PropertyListItem } from '../../models/properties.model';

@Component({
  selector: 'app-property-list-card',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './property-list-card.html',
  styleUrl: './property-list-card.scss'
})
export class PropertyListCardComponent {
  readonly property = input.required<PropertyListItem>();
}
