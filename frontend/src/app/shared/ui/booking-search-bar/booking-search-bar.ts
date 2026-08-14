import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
  ViewChild,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { DateRangePickerComponent } from '../date-range-picker/date-range-picker';
import { DestinationAutocompleteComponent } from '../destination-autocomplete/destination-autocomplete';
import { GuestsPickerComponent } from '../guests-picker/guests-picker';

/** Valores emitidos por el booking-bar (misma forma que WelcomeSearchState). */
export interface BookingSearchValues {
  destination: string;
  checkIn: string;
  checkOut: string;
  adults: number;
  children: number;
  rooms: number;
}

/**
 * Caja de búsqueda compartida (destino + fechas + huéspedes) — la misma que
 * el /welcome usa en su hero. Un solo widget para todo el flujo del huésped:
 * el /search la monta arriba y el /welcome en el hero, con el mismo
 * destination-autocomplete, date-range-picker y guests-picker.
 *
 * - `valueChange` emite ante cualquier cambio (persistencia en vivo).
 * - `search` emite al pulsar Buscar (navegación).
 */
@Component({
  selector: 'app-booking-search-bar',
  imports: [ReactiveFormsModule, DestinationAutocompleteComponent, DateRangePickerComponent, GuestsPickerComponent],
  templateUrl: './booking-search-bar.html',
  styleUrl: './booking-search-bar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BookingSearchBarComponent {
  private readonly formBuilder = inject(FormBuilder);

  readonly destination = input('');
  readonly checkIn = input('');
  readonly checkOut = input('');
  readonly adults = input(2);
  readonly children = input(0);
  readonly rooms = input(1);
  /** Fecha mínima para el calendario (por defecto hoy). */
  readonly minDate = input('');
  readonly submitLabel = input('Buscar');
  /** Variante compacta (barra más fina, usada por el /search en laptop). */
  readonly compact = input(false);

  readonly valueChange = output<BookingSearchValues>();
  readonly search = output<BookingSearchValues>();

  @ViewChild(DateRangePickerComponent) private readonly dateRange?: DateRangePickerComponent;

  readonly form = this.formBuilder.nonNullable.group({
    destination: [''],
    checkIn: [''],
    checkOut: [''],
    adults: ['2'],
    children: ['0'],
    rooms: ['1'],
  });

  /** Snapshot reactivo del form — los widgets reciben números vía computed. */
  private readonly formSnapshot = toSignal(this.form.valueChanges, {
    initialValue: this.form.getRawValue(),
  });

  readonly guestCounts = computed(() => {
    const fv = this.formSnapshot() ?? this.form.getRawValue();
    return {
      adults: Number(fv.adults) || 2,
      children: Number(fv.children) || 0,
      rooms: Number(fv.rooms) || 1,
    };
  });

  /** true cuando alguno de los tres filtros tiene contenido (habilita el X). */
  readonly hasClearable = computed(() => {
    const fv = this.formSnapshot() ?? this.form.getRawValue();
    return Boolean(
      (fv.destination ?? '').trim() ||
        fv.checkIn ||
        fv.checkOut ||
        Number(fv.adults) !== 2 ||
        Number(fv.children) !== 0 ||
        Number(fv.rooms) !== 1,
    );
  });

  /** true mientras el effect sincroniza inputs externos → form. */
  private syncingFromInputs = false;

  constructor() {
    // Sincroniza el form cuando los inputs externos cambian (p. ej. el /search
    // navega a otra URL y los query params cambian). El patch SÍ emite para que
    // formSnapshot (que alimenta guestCounts) se actualice; el guard en la
    // suscripción evita re-emitir valueChange por un patch interno.
    effect(() => {
      this.syncingFromInputs = true;
      this.form.patchValue({
        destination: this.destination(),
        checkIn: this.checkIn(),
        checkOut: this.checkOut(),
        adults: String(this.adults()),
        children: String(this.children()),
        rooms: String(this.rooms()),
      });
      this.syncingFromInputs = false;
    });

    // Emite valueChange ante cualquier edición del usuario (no en patch interno).
    this.form.valueChanges.subscribe(() => {
      if (this.syncingFromInputs) return;
      this.emitValueChange();
    });
  }

  // ── Widgets compartidos → form ──────────────────────────────────────────

  onDestinationChange(value: string): void {
    this.form.controls.destination.setValue(value);
  }

  onStartDateChange(date: string): void {
    this.form.controls.checkIn.setValue(date);
  }

  onEndDateChange(date: string): void {
    this.form.controls.checkOut.setValue(date);
  }

  onAdultsChange(value: number): void {
    this.form.controls.adults.setValue(String(value));
  }

  onChildrenChange(value: number): void {
    this.form.controls.children.setValue(String(value));
  }

  onRoomsChange(value: number): void {
    this.form.controls.rooms.setValue(String(value));
  }

  // ── Acciones ────────────────────────────────────────────────────────────

  submit(): void {
    const fv = this.form.getRawValue();
    this.search.emit({
      destination: fv.destination.trim(),
      checkIn: fv.checkIn,
      checkOut: fv.checkOut,
      adults: Number(fv.adults) || 2,
      children: Number(fv.children) || 0,
      rooms: Number(fv.rooms) || 1,
    });
  }

  /** Abre el calendario (usado por "Elegir fechas" de las cards del /search). */
  openDateRange(): void {
    this.dateRange?.open();
  }

  /** Limpia los tres filtros (destino, fechas, huéspedes) y re-emite la
   *  búsqueda: en el /search resetea los query params; en el /welcome
   *  navega a /search sin filtros. El reset también dispara valueChange
   *  para que la persistencia del welcome quede consistente. */
  clearFilters(): void {
    this.form.reset({ destination: '', checkIn: '', checkOut: '', adults: '2', children: '0', rooms: '1' });
    this.submit();
  }

  private emitValueChange(): void {
    const fv = this.form.getRawValue();
    this.valueChange.emit({
      destination: fv.destination.trim(),
      checkIn: fv.checkIn,
      checkOut: fv.checkOut,
      adults: Number(fv.adults) || 2,
      children: Number(fv.children) || 0,
      rooms: Number(fv.rooms) || 1,
    });
  }
}
