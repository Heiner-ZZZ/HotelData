import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  effect,
  inject,
  input,
  viewChild,
} from '@angular/core';
import maplibregl from 'maplibre-gl';
import type { Feature } from 'geojson';

import type { CompetitorMarker } from '../../../models/strategic-dashboard.model';

/** Proveedor de tiles del mapa competitivo.
 *
 * Usa OpenFreeMap (estilo Liberty) — el MISMO que ya renderiza en la página
 * hotels/compare de esta app. El servidor público de OSM y CartoDB no cargaban
 * en la red del cliente (tiles en blanco → "cuadrados perfectos" y zoom roto),
 * así que se descartan. Se expone como función para testear la config. */
export function tileLayerConfig(): { styleUrl: string; attribution: string } {
  return {
    styleUrl: 'https://tiles.openfreemap.org/styles/liberty',
    attribution: 'OpenFreeMap © OpenMapTiles · © OpenStreetMap',
  };
}

/** Círculo geográfico (polígono) alrededor de un punto, en km. */
function radiusPolygon(
  lat: number,
  lng: number,
  radiusKm: number,
  points = 72,
): Feature {
  const coords: [number, number][] = [];
  const dLat = radiusKm / 111.32;
  const dLng = radiusKm / (111.32 * Math.cos((lat * Math.PI) / 180));
  for (let i = 0; i < points; i++) {
    const t = (i / points) * 2 * Math.PI;
    coords.push([lng + dLng * Math.cos(t), lat + dLat * Math.sin(t)]);
  }
  coords.push(coords[0]);
  return {
    type: 'Feature',
    properties: {},
    geometry: { type: 'Polygon', coordinates: [coords] },
  };
}

/** Mapa competitivo de IE-H02: el propio hotel y los competidores dentro del
 *  radio, con un círculo que dibuja el alcance del rango. */
@Component({
  selector: 'app-competitive-map',
  standalone: true,
  template: `<div #mapContainer class="competitive-map__container"></div>`,
  styles: [
    `
      :host {
        display: block;
        width: 100%;
      }
      .competitive-map__container {
        height: 320px;
        border-radius: 10px;
        border: 1px solid var(--app-border);
        z-index: 1;
        overflow: hidden;
      }
    `,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CompetitiveMapComponent implements AfterViewInit {
  readonly ownLat = input<number | null>(null);
  readonly ownLng = input<number | null>(null);
  readonly ownLabel = input<string>('');
  readonly radioKm = input<number | null>(null);
  readonly markers = input<CompetitorMarker[]>([]);

  readonly mapContainer = viewChild.required<ElementRef<HTMLElement>>('mapContainer');

  private readonly destroyRef = inject(DestroyRef);

  private map: maplibregl.Map | null = null;
  private ownMarker: maplibregl.Marker | null = null;
  private compMarkers: maplibregl.Marker[] = [];

  constructor() {
    effect(() => {
      // Re-dibuja marcadores y radio cuando cambian los inputs (datos async).
      this.markers();
      this.ownLat();
      this.ownLng();
      this.radioKm();
      if (this.map && this.map.loaded()) this.redraw();
    });
    this.destroyRef.onDestroy(() => {
      this.clearMarkers();
      this.map?.remove();
      this.map = null;
    });
  }

  ngAfterViewInit(): void {
    const el = this.mapContainer().nativeElement;
    const cfg = tileLayerConfig();
    this.map = new maplibregl.Map({
      container: el,
      style: cfg.styleUrl,
      center: [-78.4678, -0.1807],
      zoom: 12,
      attributionControl: false,
    });
    this.map.addControl(new maplibregl.NavigationControl(), 'top-right');
    this.map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left');
    this.map.on('load', () => this.redraw());
  }

  private redraw(): void {
    if (!this.map) return;
    this.clearMarkers();
    this.removeRadius();

    const bounds = new maplibregl.LngLatBounds();
    const ownLat = this.ownLat();
    const ownLng = this.ownLng();
    let hasPoint = false;

    if (ownLat !== null && ownLng !== null) {
      this.ownMarker = this.makeMarker(
        [ownLng, ownLat],
        'hotel',
        '#1463ff',
        this.ownLabel() || 'Tu hotel',
        this.popupHtml(this.ownLabel() || 'Tu hotel', null, null, null, true),
      ).addTo(this.map);
      bounds.extend([ownLng, ownLat]);
      hasPoint = true;

      const radius = this.radioKm();
      if (radius && radius > 0) {
        this.addRadius(ownLat, ownLng, radius);
        // Incluir el radio en los límites para que la "redonda" sea visible.
        const dLat = radius / 111.32;
        const dLng = radius / (111.32 * Math.cos((ownLat * Math.PI) / 180));
        bounds.extend([ownLng - dLng, ownLat - dLat]);
        bounds.extend([ownLng + dLng, ownLat + dLat]);
      }
    }

    for (const m of this.markers()) {
      if (m.lat === null || m.lng === null) continue;
      const marker = this.makeMarker(
        [m.lng, m.lat],
        'storefront',
        '#a78bfa',
        m.hotelLabel,
        this.popupHtml(m.hotelLabel, m.adr, m.rating, m.distanceKm, false),
      ).addTo(this.map);
      this.compMarkers.push(marker);
      bounds.extend([m.lng, m.lat]);
      hasPoint = true;
    }

    if (hasPoint) {
      this.map.fitBounds(bounds, { padding: 50, maxZoom: 15, duration: 0 });
    }
  }

  private makeMarker(
    lngLat: [number, number],
    symbol: string,
    color: string,
    title: string,
    popupHtml: string,
  ): maplibregl.Marker {
    const el = document.createElement('div');
    el.innerHTML = `<span class="material-symbols-outlined" style="font-size:1.4rem;color:${color}">${symbol}</span>`;
    el.title = title;
    return new maplibregl.Marker({ element: el, anchor: 'bottom' })
      .setLngLat(lngLat)
      .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(popupHtml));
  }

  private addRadius(lat: number, lng: number, radiusKm: number): void {
    if (!this.map) return;
    if (this.map.getSource('radius')) this.removeRadius();
    this.map.addSource('radius', {
      type: 'geojson',
      data: radiusPolygon(lat, lng, radiusKm),
    });
    this.map.addLayer({
      id: 'radius-fill',
      type: 'fill',
      source: 'radius',
      paint: { 'fill-color': '#1463ff', 'fill-opacity': 0.06 },
    });
    this.map.addLayer({
      id: 'radius-line',
      type: 'line',
      source: 'radius',
      paint: { 'line-color': '#1463ff', 'line-width': 1, 'line-dasharray': [3, 2] },
    });
  }

  private removeRadius(): void {
    if (!this.map) return;
    for (const id of ['radius-line', 'radius-fill']) {
      if (this.map.getLayer(id)) this.map.removeLayer(id);
    }
    if (this.map.getSource('radius')) this.map.removeSource('radius');
  }

  private clearMarkers(): void {
    this.ownMarker?.remove();
    this.ownMarker = null;
    for (const m of this.compMarkers) m.remove();
    this.compMarkers = [];
  }

  private popupHtml(
    label: string,
    adr: number | null,
    rating: number | null,
    distanceKm: number | null,
    isSelf: boolean,
  ): string {
    const rows: string[] = [];
    rows.push(`<strong style="font-size:0.92rem">${this.escapeHtml(label)}</strong>`);
    if (isSelf) rows.push(`<div style="color:#5f6f87;font-size:0.8rem">Tu hotel</div>`);
    if (adr !== null) rows.push(`<div style="color:#5f6f87;font-size:0.8rem">ADR $${adr.toFixed(2)}</div>`);
    if (rating !== null) rows.push(`<div style="color:#5f6f87;font-size:0.8rem">★ ${rating.toFixed(1)}</div>`);
    if (distanceKm !== null) rows.push(`<div style="color:#5f6f87;font-size:0.8rem">A ${distanceKm.toFixed(2)} km</div>`);
    return `<div style="font-family:inherit;min-width:150px;display:grid;gap:2px">${rows.join('')}</div>`;
  }

  private escapeHtml(value: string): string {
    return value.replace(/[&<>"']/g, (c) => {
      const map: Record<string, string> = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      };
      return map[c];
    });
  }
}
