import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-sort-control',
  template: `
    <div class="sort-control surface-card">
      <div class="copy-block">
        @if (totalIsEstimate()) {
          <strong>{{ pageSize() }} hoteles por página</strong>
          <span>Disponibilidad real · página {{ page() }}</span>
        } @else {
          <strong>{{ total() }} hotel{{ total() !== 1 ? 'es' : '' }} encontrados</strong>
        }
      </div>
      <div class="actions">
        <button type="button" (click)="previous.emit()" [disabled]="!hasPrev()">Anterior</button>
        <span>
          @if (totalIsEstimate()) {
            Página {{ page() }} · {{ hasNext() ? 'hay más resultados' : 'última página' }}
          } @else {
            Página {{ page() }} de {{ totalPages() || 1 }}
          }
        </span>
        <button type="button" (click)="next.emit()" [disabled]="!hasNext()">Siguiente</button>
      </div>
    </div>
  `,
  styles: `
    .sort-control {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 0.875rem 1rem;
    }
    .copy-block {
      display: grid;
      gap: 0.25rem;
    }
    strong,
    span {
      margin: 0;
    }
    span {
      color: var(--muted-text);
      font-size: 0.875rem;
    }
    .actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }
    button {
      min-height: 2.4rem;
      padding: 0 0.875rem;
      border-radius: 8px;
      border: 1px solid var(--app-border);
      background: var(--surface);
      color: var(--app-text);
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s, color 0.15s;
    }
    button:hover:not(:disabled) {
      background: var(--surface-hover);
      border-color: var(--accent);
      color: var(--accent);
    }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.5;
    }
    @media (max-width: 920px) {
      .sort-control {
        align-items: start;
        flex-direction: column;
      }
    }
  `
})
export class SortControlComponent {
  readonly total = input(0);
  readonly page = input(1);
  readonly totalPages = input(0);
  readonly totalIsEstimate = input(false);
  readonly pageSize = input(10);
  readonly hasPrev = input(false);
  readonly hasNext = input(false);
  readonly previous = output<void>();
  readonly next = output<void>();
}
