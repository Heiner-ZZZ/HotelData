import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';
import { httpResource } from '@angular/common/http';

import { API_CONFIG } from '../../../core/api/api.config';

export type DestinationType = 'city' | 'hotel' | 'country';

export interface DestinationSuggestion {
  id: number | string;
  name: string;
  type: DestinationType;
}

interface SuggestDto {
  items: { id: number | string; name: string; type: DestinationType }[];
}

@Component({
  selector: 'app-destination-autocomplete',
  imports: [],
  templateUrl: './destination-autocomplete.html',
  styleUrl: './destination-autocomplete.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DestinationAutocompleteComponent {
  private readonly apiConfig = inject(API_CONFIG);

  /** Valor externo (form control del padre) que se refleja en el input. */
  readonly value = input('');
  /** Mínimo de caracteres para disparar sugerencias. */
  readonly minChars = input(2);
  /** id/name del input — el padre puede pasarlo para que su <label for="…">
   *  lo asocie (el booking-bar usa booking-bar-dest). Sin él, el input no
   *  tiene id/name y Chrome Issues lo reporta. */
  readonly inputId = input('destination-input');

  /** Se emite en cada edición (input del usuario). */
  readonly valueChange = output<string>();
  /** Se emite cuando el usuario elige una opción del dropdown. */
  readonly select = output<string>();

  readonly filterText = signal('');
  readonly dropdownOpen = signal(false);
  readonly highlighted = signal(-1);
  /** El usuario está interactuando con el input (focus). El dropdown solo se
   *  auto-abre cuando hay interacción real — nunca por un valor precargado
   *  desde afuera (p. ej. ?destination=… en /search, que dispara una petición
   *  al montar y de otro modo abriría el dropdown sin que el usuario toque nada). */
  readonly focused = signal(false);

  /** Término debounced que dispara el httpResource. */
  private readonly debouncedTerm = signal('');

  readonly suggestionsResource = httpResource<DestinationSuggestion[]>(() => {
    const term = this.debouncedTerm();
    if (!term) return undefined;
    return {
      url: `${this.apiConfig.baseUrl}/hotels/destinations/suggest?q=${encodeURIComponent(term)}&limit=8`,
      method: 'GET' as const,
      withCredentials: true,
    };
  }, {
    parse: (dto) => {
      const raw = dto as SuggestDto;
      return (raw.items ?? []).map((it) => ({ id: it.id, name: it.name, type: it.type ?? 'city' }));
    },
  });

  /** Lista editable de sugerencias — el resource la reemplaza vía efecto. */
  readonly suggestions = signal<DestinationSuggestion[]>([]);
  readonly loading = computed(() => this.suggestionsResource.isLoading());
  /** Expose el término debounced al template (spinner visible solo si hay búsqueda activa). */
  readonly debouncedTermVisible = computed(() => this.debouncedTerm().length > 0);

  constructor() {
    // Debounce del texto escrito (250ms) antes de disparar la petición.
    let firstRun = true;
    effect((onCleanup) => {
      const term = this.filterText();
      if (firstRun) {
        firstRun = false;
        return;
      }
      const timer = setTimeout(() => {
        const t = term.trim();
        if (t.length >= this.minChars()) {
          this.debouncedTerm.set(t);
        } else {
          this.debouncedTerm.set('');
          this.dropdownOpen.set(false);
        }
      }, 250);
      onCleanup(() => clearTimeout(timer));
    });

    // Reflejar el valor externo (form control) en el input editable, SIN
    // pisar la escritura del usuario: solo sincroniza cuando el valor EXTERNO
    // cambia (guard lastSeenValue + untracked, mismo patrón que property-selector).
    let lastSeenValue: string | null = null;
    effect(() => {
      const v = this.value();
      if (v === lastSeenValue) return;
      lastSeenValue = v;
      untracked(() => {
        if (this.filterText() !== v) this.filterText.set(v);
      });
    });

    // Bridge: resource → suggestions (writable), y abrir el dropdown SOLO si
    // el usuario está interactuando (focus). Sin este guard, un destino
    // precargado (?destination=… en /search o el localStorage del welcome)
    // dispara una petición al montar y abre el dropdown sin interacción.
    effect(() => {
      const items = this.suggestionsResource.value();
      if (!items) return;
      this.suggestions.set(items);
      if (this.debouncedTerm() && items.length > 0 && this.focused()) {
        this.dropdownOpen.set(true);
      }
    });
  }

  onInput(value: string): void {
    this.filterText.set(value);
    this.highlighted.set(-1);
    this.valueChange.emit(value);
  }

  onFocus(): void {
    this.focused.set(true);
    if (this.debouncedTerm() && this.suggestions().length > 0) {
      this.dropdownOpen.set(true);
    }
  }

  onBlur(): void {
    this.focused.set(false);
  }

  onKeydown(event: KeyboardEvent): void {
    const items = this.suggestions();
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.highlighted.update((h) => Math.min(h + 1, items.length - 1));
      this.dropdownOpen.set(true);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.highlighted.update((h) => Math.max(h - 1, 0));
      this.dropdownOpen.set(true);
    } else if (event.key === 'Enter') {
      const h = this.highlighted();
      if (h >= 0 && items[h]) {
        event.preventDefault();
        this.choose(items[h]);
      }
    } else if (event.key === 'Escape') {
      this.dropdownOpen.set(false);
    }
  }

  choose(item: DestinationSuggestion): void {
    this.filterText.set(item.name);
    this.valueChange.emit(item.name);
    this.select.emit(item.name);
    this.dropdownOpen.set(false);
    this.highlighted.set(-1);
  }

  /** Icono Material Symbols por tipo de lugar. */
  typeIcon(type: DestinationType): string {
    if (type === 'hotel') return 'hotel';
    if (type === 'country') return 'public';
    return 'location_city';
  }

  /** Label corto por tipo (País / Hotel / Ciudad). */
  typeLabel(type: DestinationType): string {
    if (type === 'hotel') return 'Hotel';
    if (type === 'country') return 'País';
    return 'Ciudad';
  }

  @HostListener('document:click', ['$event'])
  closeOnOutsideClick(event: Event): void {
    const target = event.target as HTMLElement;
    if (!target.closest('.da-autocomplete')) {
      this.dropdownOpen.set(false);
    }
  }
}
