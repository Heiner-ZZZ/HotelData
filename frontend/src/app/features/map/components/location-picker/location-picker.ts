import { ChangeDetectionStrategy, Component, computed, effect, ElementRef, input, output, viewChild } from '@angular/core';
import * as L from 'leaflet';

@Component({
  selector: 'app-location-picker',
  imports: [],
  template: `
    <div class="location-picker-wrap">
      <div #mapContainer class="map-container"></div>
      <div class="coords-display">
        <span class="coord-label">Latitud: <strong>{{ displayLat() }}</strong></span>
        <span class="coord-label">Longitud: <strong>{{ displayLng() }}</strong></span>
      </div>
    </div>
  `,
  styles: [`
    .location-picker-wrap { display: grid; gap: 0.5rem; }
    .map-container { height: 300px; border-radius: 8px; border: 1px solid var(--border-color, #e2e8f0); z-index: 1; }
    .coords-display { display: flex; gap: 1rem; font-size: 0.8125rem; }
    .coord-label { color: var(--muted-text, #64748b); }
    .coord-label strong { color: var(--text-color, #1e293b); font-weight: 600; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LocationPickerComponent {
  readonly lat = input<number | null>(null);
  readonly lng = input<number | null>(null);
  readonly locationChange = output<{ latitude: number; longitude: number }>();

  readonly mapContainer = viewChild.required<ElementRef<HTMLElement>>('mapContainer');

  readonly displayLat = computed(() => this.lat() !== null ? this.lat()!.toFixed(6) : '—');
  readonly displayLng = computed(() => this.lng() !== null ? this.lng()!.toFixed(6) : '—');

  private map: L.Map | null = null;
  private marker: L.Marker | null = null;
  private defaultCoords: [number, number] = [19.4326, -99.1332]; // Mexico City center

  constructor() {
    effect(() => {
      const lat = this.lat();
      const lng = this.lng();
      if (lat !== null && lng !== null && this.map) {
        this.setMarkerPosition(lat, lng);
      }
    });
  }

  ngAfterViewInit() {
    this.initMap();
  }

  private initMap() {
    const el = this.mapContainer().nativeElement;
    const lat = this.lat() ?? this.defaultCoords[0];
    const lng = this.lng() ?? this.defaultCoords[1];

    this.map = L.map(el, {
      center: [lat, lng],
      zoom: 5,
      zoomControl: true,
      attributionControl: false,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
    }).addTo(this.map);

    this.setMarkerPosition(lat, lng);

    this.map.on('click', (e: L.LeafletMouseEvent) => {
      const newLat = parseFloat(e.latlng.lat.toFixed(6));
      const newLng = parseFloat(e.latlng.lng.toFixed(6));
      this.setMarkerPosition(newLat, newLng);
      this.locationChange.emit({ latitude: newLat, longitude: newLng });
    });
  }

  private setMarkerPosition(lat: number, lng: number) {
    if (!this.map) return;

    const pinIcon = L.divIcon({
      html: '<span style="font-size:28px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.3))">📍</span>',
      className: '',
      iconSize: [28, 28],
      iconAnchor: [14, 28],
      popupAnchor: [0, -28],
    });

    if (this.marker) {
      this.marker.setLatLng([lat, lng]);
    } else {
      this.marker = L.marker([lat, lng], { icon: pinIcon, draggable: true }).addTo(this.map);
      this.marker.on('dragend', () => {
        const pos = this.marker!.getLatLng();
        const newLat = parseFloat(pos.lat.toFixed(6));
        const newLng = parseFloat(pos.lng.toFixed(6));
        this.marker!.setLatLng([newLat, newLng]);
        this.locationChange.emit({ latitude: newLat, longitude: newLng });
      });
    }
    this.map.setView([lat, lng], this.map.getZoom());
  }
}
