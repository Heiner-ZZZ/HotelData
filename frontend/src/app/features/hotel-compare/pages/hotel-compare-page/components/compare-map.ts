import { AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, input, OnDestroy, viewChild } from '@angular/core';
import maplibregl from 'maplibre-gl';
import type { HotelCompareItem } from '../../../models/hotel-compare.model';

@Component({
  selector: 'app-compare-map',
  templateUrl: './compare-map.html',
  styleUrl: './compare-map.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CompareMapComponent implements OnDestroy, AfterViewInit {
  readonly hotels = input<HotelCompareItem[]>([]);

  private readonly _mapContainer = viewChild<ElementRef<HTMLElement>>('mapContainer');
  private _map: maplibregl.Map | null = null;
  private _userMarker: maplibregl.Marker | null = null;
  private _hotelMarkers: maplibregl.Marker[] = [];

  ngAfterViewInit() {
    const el = this._mapContainer();
    if (!el) return;

    this._map = new maplibregl.Map({
      container: el.nativeElement,
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: [-93.0, 23.0],
      zoom: 5,
      attributionControl: false,
    });

    this._map.addControl(new maplibregl.NavigationControl(), 'top-right');
    this._map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left');

    this._map.on('load', () => this._placeMarkers());
  }

  private _placeMarkers() {
    const items = this.hotels();
    if (!items.length || !this._map) return;

    this._destroyMarkers();

    const bounds = new maplibregl.LngLatBounds();
    const colours = ['#1463FF', '#059669', '#D97706'];

    for (let i = 0; i < items.length; i++) {
      const h = items[i];
      const colour = colours[i % colours.length];

      const markerEl = document.createElement('div');
      markerEl.className = 'hotel-marker';
      markerEl.innerHTML = `<span class="material-symbols-outlined" style="font-size:1.5rem;color:${colour}">hotel</span>`;
      markerEl.title = h.hotelName;

      const marker = new maplibregl.Marker({ element: markerEl, anchor: 'bottom' })
        .setLngLat([h.longitude, h.latitude])
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(`
            <div class="map-popup">
              <strong>${h.hotelName}</strong>
              ${h.minNightlyRateLabel ? `<div class="map-popup-price">Desde ${h.minNightlyRateLabel}/noche</div>` : ''}
              ${h.propStarrating ? `<div class="map-popup-stars">${'★'.repeat(Math.round(h.propStarrating))} ${h.propStarrating}</div>` : ''}
              ${h.propReviewScore ? `<div class="map-popup-score">Puntuación: ${h.propReviewScore.toFixed(1)}</div>` : ''}
            </div>
          `),
        )
        .addTo(this._map);

      this._hotelMarkers.push(marker);
      bounds.extend([h.longitude, h.latitude]);
    }

    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          this._addUserMarker(lat, lng);
          bounds.extend([lng, lat]);
          this._map?.fitBounds(bounds, { padding: 60, maxZoom: 10 });
        },
        () => {
          this._map?.fitBounds(bounds, { padding: 60, maxZoom: 10 });
        },
      );
    } else {
      this._map?.fitBounds(bounds, { padding: 60, maxZoom: 10 });
    }
  }

  private _addUserMarker(lat: number, lng: number) {
    if (!this._map) return;
    this._userMarker?.remove();

    const el = document.createElement('div');
    el.className = 'user-marker';
    el.innerHTML = `<span class="material-symbols-outlined" style="font-size:1.4rem;color:#D32F2F">person_pin_circle</span>`;
    el.title = 'Tu ubicación';

    this._userMarker = new maplibregl.Marker({ element: el, anchor: 'bottom' })
      .setLngLat([lng, lat])
      .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(`<div class="map-popup"><strong>Tu ubicación</strong></div>`))
      .addTo(this._map);
  }

  private _destroyMarkers() {
    for (const m of this._hotelMarkers) m.remove();
    this._hotelMarkers = [];
    this._userMarker?.remove();
    this._userMarker = null;
  }

  fitMapToHotels() {
    const items = this.hotels();
    if (!items.length || !this._map) return;
    const bounds = new maplibregl.LngLatBounds();
    for (const h of items) {
      bounds.extend([h.longitude, h.latitude]);
    }
    this._map.fitBounds(bounds, { padding: 60, maxZoom: 10 });
  }

  ngOnDestroy() {
    this._destroyMarkers();
    this._map?.remove();
    this._map = null;
  }
}
