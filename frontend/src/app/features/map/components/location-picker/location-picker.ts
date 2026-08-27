import { AfterViewInit, ChangeDetectionStrategy, Component, DestroyRef, ElementRef, computed, effect, inject, input, output, viewChild } from '@angular/core';
import maplibregl from 'maplibre-gl';

/** Proveedor de tiles compartido con compare-map y competitive-map.
 *  OpenFreeMap (estilo Liberty) — el servidor público de OSM no carga en la
 *  red del cliente (tiles en blanco), ver competitive-map.ts. */
export function mapTileStyleUrl(): string {
  return 'https://tiles.openfreemap.org/styles/liberty';
}

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
    :host { display: block; width: 100%; min-width: 0; }
    .location-picker-wrap { display: grid; gap: 0.5rem; }
    .map-container { height: clamp(320px, 46vh, 560px); width: 100%; border-radius: 8px; border: 1px solid var(--app-border); z-index: 1; }
    .coords-display { display: flex; gap: 1rem; font-size: 0.8125rem; }
    .coord-label { color: var(--muted-text); }
    .coord-label strong { color: var(--app-text); font-weight: 600; }
    .picker-pin .material-symbols-outlined {
      font-size: 1.75rem;
      color: #D32F2F;
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LocationPickerComponent implements AfterViewInit {
  readonly lat = input<number | null>(null);
  readonly lng = input<number | null>(null);
  readonly locationChange = output<{ latitude: number; longitude: number }>();

  private readonly destroyRef = inject(DestroyRef);

  readonly mapContainer = viewChild.required<ElementRef<HTMLElement>>('mapContainer');

  readonly displayLat = computed(() => this.lat() !== null ? this.lat()!.toFixed(6) : '—');
  readonly displayLng = computed(() => this.lng() !== null ? this.lng()!.toFixed(6) : '—');

  private map: maplibregl.Map | null = null;
  private marker: maplibregl.Marker | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private defaultCoords: [number, number] = [19.4326, -99.1332]; // Mexico City center

  constructor() {
    effect(() => {
      const lat = this.lat();
      const lng = this.lng();
      if (lat !== null && lng !== null && this.map) {
        this.setMarkerPosition(lat, lng);
      }
    });
    this.destroyRef.onDestroy(() => {
      this.resizeObserver?.disconnect();
      this.resizeObserver = null;
      this.marker?.remove();
      this.marker = null;
      this.map?.remove();
      this.map = null;
    });
  }

  ngAfterViewInit() {
    this.initMap();
  }

  private initMap() {
    const el = this.mapContainer().nativeElement;
    const lat = this.lat() ?? this.defaultCoords[0];
    const lng = this.lng() ?? this.defaultCoords[1];

    this.map = new maplibregl.Map({
      container: el,
      style: mapTileStyleUrl(),
      center: [lng, lat],
      zoom: 5,
      attributionControl: false,
    });

    this.map.addControl(new maplibregl.NavigationControl(), 'top-right');
    this.map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left');

    this.resizeObserver = this.observeResize(el);

    this.setMarkerPosition(lat, lng);

    this.map.on('click', (e: maplibregl.MapMouseEvent) => {
      const newLat = parseFloat(e.lngLat.lat.toFixed(6));
      const newLng = parseFloat(e.lngLat.lng.toFixed(6));
      this.setMarkerPosition(newLat, newLng);
      this.locationChange.emit({ latitude: newLat, longitude: newLng });
    });
  }

  /** Re-encuadra el canvas cuando el contenedor cambia de tamaño (responsive).
   *  Sin esto el mapa renderiza al tamaño inicial y queda estirado/cortado al
   *  rotar el móvil, cambiar de layout o reabrirse — el mismo problema que
   *  tenían los mapas del onboarding. Se ignora el ancho 0 (contenedor oculto)
   *  para no llamar resize() con un tamaño fantasma. */
  private observeResize(el: HTMLElement): ResizeObserver | null {
    if (typeof ResizeObserver === 'undefined') return null; // guard jsdom/SSR
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect?.width ?? 0;
      if (width > 0) this.map?.resize();
    });
    observer.observe(el);
    return observer;
  }

  private setMarkerPosition(lat: number, lng: number) {
    if (!this.map) return;

    if (this.marker) {
      this.marker.setLngLat([lng, lat]);
    } else {
      const markerEl = document.createElement('div');
      markerEl.className = 'picker-pin';
      markerEl.innerHTML = '<span class="material-symbols-outlined">location_on</span>';
      this.marker = new maplibregl.Marker({ element: markerEl, anchor: 'bottom', draggable: true })
        .setLngLat([lng, lat])
        .addTo(this.map);
      this.marker.on('dragend', () => {
        const pos = this.marker!.getLngLat();
        const newLat = parseFloat(pos.lat.toFixed(6));
        const newLng = parseFloat(pos.lng.toFixed(6));
        this.marker!.setLngLat([newLng, newLat]);
        this.locationChange.emit({ latitude: newLat, longitude: newLng });
      });
    }
    this.map.easeTo({ center: [lng, lat], duration: 200 });
  }
}
