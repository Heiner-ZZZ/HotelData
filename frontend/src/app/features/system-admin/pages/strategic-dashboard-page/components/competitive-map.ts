import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  effect,
  input,
  viewChild,
} from '@angular/core';
import * as L from 'leaflet';

import type { CompetitorMarker } from '../../../models/strategic-dashboard.model';

/** Mapa competitivo de IE-H02: muestra el propio hotel y los competidores
 *  dentro del radio, con un círculo que dibuja el alcance del rango. */
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

  private map: L.Map | null = null;
  private markerLayer: L.LayerGroup | null = null;
  private radiusCircle: L.Circle | null = null;

  constructor() {
    effect(() => {
      // Re-dibuja marcadores y radio cuando cambian los inputs (datos async).
      this.markers();
      this.ownLat();
      this.ownLng();
      this.radioKm();
      if (this.map) this.redraw();
    });
  }

  ngAfterViewInit(): void {
    this.initMap();
    this.redraw();
  }

  private initMap(): void {
    if (this.map) return;
    const el = this.mapContainer().nativeElement;
    this.map = L.map(el, {
      center: [0, 0],
      zoom: 13,
      zoomControl: true,
      attributionControl: false,
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
    }).addTo(this.map);
    this.markerLayer = L.layerGroup().addTo(this.map);
  }

  private redraw(): void {
    if (!this.map || !this.markerLayer) return;
    this.markerLayer.clearLayers();
    if (this.radiusCircle) {
      this.radiusCircle.remove();
      this.radiusCircle = null;
    }

    const bounds: L.LatLng[] = [];
    const ownLat = this.ownLat();
    const ownLng = this.ownLng();

    if (ownLat !== null && ownLng !== null) {
      const ownPoint = L.latLng(ownLat, ownLng);
      bounds.push(ownPoint);
      this.markerLayer.addLayer(
        L.marker(ownPoint, { icon: this.pinIcon('hotel', 'var(--accent)', true) }).bindPopup(
          this.popupHtml(this.ownLabel() || 'Tu hotel', null, null, null, true),
        ),
      );
      const radius = this.radioKm();
      if (radius && radius > 0) {
        this.radiusCircle = L.circle(ownPoint, {
          radius: radius * 1000,
          color: 'var(--accent)',
          fillColor: 'var(--accent)',
          fillOpacity: 0.06,
          weight: 1,
          dashArray: '4 4',
        }).addTo(this.map);
      }
    }

    for (const m of this.markers()) {
      if (m.lat === null || m.lng === null) continue;
      const point = L.latLng(m.lat, m.lng);
      bounds.push(point);
      this.markerLayer.addLayer(
        L.marker(point, { icon: this.pinIcon('storefront', 'var(--purple)', false) }).bindPopup(
          this.popupHtml(m.hotelLabel, m.adr, m.rating, m.distanceKm, false),
        ),
      );
    }

    if (bounds.length > 1) {
      this.map.fitBounds(L.latLngBounds(bounds), { padding: [40, 40], maxZoom: 16 });
    } else if (bounds.length === 1) {
      this.map.setView(bounds[0], 13);
    }
  }

  /** Marcador circular token-driven (sin emojis): icono Material Symbols
   *  centrado sobre un pin de color semántico. */
  private pinIcon(symbol: string, color: string, isSelf: boolean): L.DivIcon {
    const size = isSelf ? 30 : 26;
    return L.divIcon({
      className: '',
      html: `
        <div style="
          width:${size}px;height:${size}px;border-radius:50%;
          background:${color};border:2px solid var(--surface,#fff);
          box-shadow:0 1px 4px rgba(0,0,0,.3);
          display:flex;align-items:center;justify-content:center;
          color:var(--on-accent,#fff);font-size:16px;">
          <span class="material-symbols-outlined" style="font-size:${isSelf ? 16 : 14}px;">${symbol}</span>
        </div>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size],
      popupAnchor: [0, -size],
    });
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
    if (isSelf) rows.push(`<span style="color:var(--muted-text);font-size:0.8rem">Tu hotel</span>`);
    if (adr !== null) rows.push(`<span style="color:var(--muted-text);font-size:0.8rem">ADR $${adr.toFixed(2)}</span>`);
    if (rating !== null) rows.push(`<span style="color:var(--muted-text);font-size:0.8rem">★ ${rating.toFixed(1)}</span>`);
    if (distanceKm !== null) rows.push(`<span style="color:var(--muted-text);font-size:0.8rem">A ${distanceKm.toFixed(2)} km</span>`);
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
