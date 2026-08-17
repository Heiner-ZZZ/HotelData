import {
  ChangeDetectionStrategy,
  Component,
  computed,
  HostListener,
  input,
  output,
  signal,
} from '@angular/core';

interface StepperRow {
  key: 'adults' | 'children' | 'rooms';
  label: string;
  value: number;
  min: number;
  max: number;
}

@Component({
  selector: 'app-guests-picker',
  imports: [],
  templateUrl: './guests-picker.html',
  styleUrl: './guests-picker.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GuestsPickerComponent {
  readonly adults = input(2);
  readonly children = input(0);
  readonly rooms = input(1);

  readonly adultsChange = output<number>();
  readonly childrenChange = output<number>();
  readonly roomsChange = output<number>();

  readonly isOpen = signal(false);

  /** Resumen legible para el trigger: "3 huéspedes · 2 habitaciones". */
  readonly summaryLabel = computed(() => {
    const guests = this.adults() + this.children();
    const rooms = this.rooms();
    return `${guests} ${guests === 1 ? 'huésped' : 'huéspedes'} · ${rooms} ${rooms === 1 ? 'habitación' : 'habitaciones'}`;
  });

  readonly rows = computed<StepperRow[]>(() => [
    { key: 'adults', label: 'Adultos', value: this.adults(), min: 1, max: 9 },
    { key: 'children', label: 'Niños', value: this.children(), min: 0, max: 6 },
    { key: 'rooms', label: 'Habitaciones', value: this.rooms(), min: 1, max: 5 },
  ]);

  toggleOpen(): void {
    this.isOpen.update((v) => !v);
  }

  close(): void {
    this.isOpen.set(false);
  }

  /** Escape cierra el popover (WCAG 2.1.1 — sin trampa de teclado). */
  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.isOpen()) this.close();
  }

  adjust(key: 'adults' | 'children' | 'rooms', delta: number): void {
    const row = this.rows().find((r) => r.key === key);
    if (!row) return;
    const next = Math.min(Math.max(row.value + delta, row.min), row.max);
    if (next === row.value) return;
    if (key === 'adults') this.adultsChange.emit(next);
    if (key === 'children') this.childrenChange.emit(next);
    if (key === 'rooms') this.roomsChange.emit(next);
  }
}
