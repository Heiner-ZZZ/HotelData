import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-availability-cell',
  standalone: true,
  templateUrl: './availability-cell.html',
  styleUrl: './availability-cell.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AvailabilityCellComponent {
  readonly type = input<'number' | 'checkbox'>('number');
  readonly value = input<number | boolean | null>(null);
  readonly min = input<number | null>(null);
  readonly step = input<number | null>(1);
  readonly invalid = input(false);
  readonly label = input('');

  readonly valueChanged = output<number | boolean | null>();

  onNumericInput(event: Event) {
    const target = event.target as HTMLInputElement;
    const value = target.value === '' ? null : Number(target.value);
    this.valueChanged.emit(Number.isNaN(value) ? null : value);
  }

  onCheckboxChange(event: Event) {
    const target = event.target as HTMLInputElement;
    this.valueChanged.emit(target.checked);
  }
}
