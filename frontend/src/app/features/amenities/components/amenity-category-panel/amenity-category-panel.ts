import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';

import type { AmenityCategoryViewModel } from '../../models/amenities.model';
import { amenityIcon } from '../../utils/amenity-icons';

@Component({
  selector: 'app-amenity-category-panel',
  templateUrl: './amenity-category-panel.html',
  styleUrl: './amenity-category-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AmenityCategoryPanelComponent {
  readonly category = input.required<AmenityCategoryViewModel>();
  readonly toggleAmenity = output<string>();
  readonly selectedLabels = input.required<Set<string>>();
  readonly searchTerm = input<string>('');
  readonly amenityPrices = input<Map<string, number>>(new Map());
  readonly updatePrice = output<{ label: string; value: string }>();

  readonly expanded = signal(true);

  toggleCollapse() {
    this.expanded.update((v) => !v);
  }

  onToggle(label: string) {
    this.toggleAmenity.emit(label);
  }

  onPriceInput(label: string, event: Event) {
    const value = (event.target as HTMLInputElement).value;
    this.updatePrice.emit({ label, value });
  }

  getPrice(label: string): number {
    return this.amenityPrices().get(label) ?? 0;
  }

  getAmenityIcon(label: string): string {
    return amenityIcon(label);
  }

  getCategoryIcon(categoryName: string): string {
    const name = categoryName.toLowerCase();
    if (name.includes('wifi') || name.includes('internet') || name.includes('conexión') || name.includes('conectividad')) return 'wifi';
    if (name.includes('estacionamiento') || name.includes('parqueo') || name.includes('parking') || name.includes('cochera')) return 'local_parking';
    if (name.includes('piscina') || name.includes('alberca') || name.includes('pool') || name.includes('jacuzzi')) return 'pool';
    if (name.includes('comida') || name.includes('restaurante') || name.includes('desayuno') || name.includes('bebida') || name.includes('gastronomía') || name.includes('bar')) return 'restaurant';
    if (name.includes('spa') || name.includes('bienestar') || name.includes('masaje') || name.includes('sauna') || name.includes('terma')) return 'spa';
    if (name.includes('habitaci') || name.includes('dormitorio') || name.includes('room') || name.includes('cama')) return 'meeting_room';
    if (name.includes('servicio') || name.includes('recepción') || name.includes('conserje') || name.includes('limpieza')) return 'room_service';
    if (name.includes('salud') || name.includes('gimnasio') || name.includes('deporte') || name.includes('gym') || name.includes('entrenamiento')) return 'fitness_center';
    if (name.includes('popular') || name.includes('destacado') || name.includes('favorito') || name.includes('común')) return 'star';
    if (name.includes('mascota') || name.includes('perro') || name.includes('pet') || name.includes('animal')) return 'pets';
    if (name.includes('aire') || name.includes('clima') || name.includes('calefac') || name.includes('ac ')) return 'ac_unit';
    if (name.includes('negocio') || name.includes('reunión') || name.includes('evento') || name.includes('sala')) return 'business_center';
    if (name.includes('accesibil') || name.includes('silla') || name.includes('rampa')) return 'accessible';
    return 'check_box';
  }

  /**
   * Split a label into text segments, marking the portion that matches
   * the current search term so the template can highlight it.
   */
  highlightLabel(label: string): { text: string; highlighted: boolean }[] {
    const term = this.searchTerm();
    if (!term) {
      return [{ text: label, highlighted: false }];
    }
    const lowerLabel = label.toLowerCase();
    const lowerTerm = term.toLowerCase();
    const segments: { text: string; highlighted: boolean }[] = [];
    let cursor = 0;
    let idx = lowerLabel.indexOf(lowerTerm, cursor);
    while (idx !== -1) {
      if (idx > cursor) {
        segments.push({ text: label.slice(cursor, idx), highlighted: false });
      }
      segments.push({ text: label.slice(idx, idx + lowerTerm.length), highlighted: true });
      cursor = idx + lowerTerm.length;
      idx = lowerLabel.indexOf(lowerTerm, cursor);
    }
    if (cursor < label.length) {
      segments.push({ text: label.slice(cursor), highlighted: false });
    }
    return segments.length ? segments : [{ text: label, highlighted: false }];
  }
}
