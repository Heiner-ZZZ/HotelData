import { Component, input } from '@angular/core';

@Component({
  selector: 'app-sort-control',
  standalone: true,
  template:
    '<div class="sort-control">{{ summary() }}</div>',
  styles:
    '.sort-control { color: var(--muted-text); font-size: 0.875rem; min-height: 1.5rem; display: flex; align-items: center; }'
})
export class SortControlComponent {
  readonly summary = input('Cargando resultados...');
}
