import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';

/**
 * Controles de carrusel compartidos: puntitos (píldora activa) + flechas
 * prev/next, con el diseño del comparador de hoteles. Un único lugar para
 * que welcome, hoteles similares, habitaciones del detalle y cualquier
 * galería futura usen exactamente los mismos indicadores.
 *
 * El componente detiene la propagación de los clics internamente (los
 * carruseles suelen vivir dentro de `<a>` / cards clickeables).
 *
 * Modo `revealOnHover`: las flechas quedan ocultas hasta que el padre marca
 * `[class.revealed]` en el host (hover de la card), o hasta el foco con
 * teclado — igual que en el comparador.
 */
@Component({
  selector: 'app-carousel-controls',
  imports: [],
  templateUrl: './carousel-controls.html',
  styleUrl: './carousel-controls.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[class.reveal-mode]': 'revealOnHover()',
  },
})
export class CarouselControlsComponent {
  /** Cantidad de fotos del carrusel (0/1 → no renderiza controles). */
  readonly count = input(0);
  /** Índice de la foto activa (define qué puntito es la píldora). */
  readonly activeIndex = input(0);
  /** Oculta las flechas hasta que el padre ponga `revealed` en el host. */
  readonly revealOnHover = input(false);
  /** Nombre del sujeto (hotel/habitación) para los aria-labels. */
  readonly subjectLabel = input('');

  readonly navigate = output<number>();
  readonly previous = output<void>();
  readonly next = output<void>();

  readonly dotIndices = computed(() => {
    const count = this.count();
    return Array.from({ length: count }, (_, i) => i);
  });

  private label(prefix: string, suffix?: number): string {
    const subject = this.subjectLabel();
    const base = subject ? `${prefix} de ${subject}` : prefix;
    return suffix !== undefined ? `${base} ${suffix}` : base;
  }

  dotLabel(index: number): string {
    return this.label('Ver foto', index + 1);
  }

  prevLabel(): string {
    return this.label('Foto anterior');
  }

  nextLabel(): string {
    return this.label('Foto siguiente');
  }

  onNavigate(index: number, event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    this.navigate.emit(index);
  }

  onPrevious(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    this.previous.emit();
  }

  onNext(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    this.next.emit();
  }
}
