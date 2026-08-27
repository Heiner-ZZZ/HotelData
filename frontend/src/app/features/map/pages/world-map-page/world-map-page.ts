import { AfterViewInit, ChangeDetectionStrategy, Component, DestroyRef, ElementRef, effect, inject, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import maplibregl from 'maplibre-gl';

import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { GeoDestination, GeoHotel } from '../../models/map.model';
import { MapApiService } from '../../services/map-api.service';
import { mapTileStyleUrl } from '../../components/location-picker/location-picker';

@Component({
  selector: 'app-world-map-page',
  imports: [LoadingStateComponent, PageHeaderComponent, RouterLink],
  templateUrl: './world-map-page.html',
  styleUrl: './world-map-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorldMapPageComponent implements AfterViewInit {
  private readonly api = inject(MapApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly mapContainer = viewChild.required<ElementRef<HTMLElement>>('mapContainer');
  readonly loaded = signal(false);
  readonly destinations = signal<GeoDestination[]>([]);
  readonly hotels = signal<GeoHotel[]>([]);

  private map: maplibregl.Map | null = null;
  private destMarkers: maplibregl.Marker[] = [];
  private hotelMarkers: maplibregl.Marker[] = [];
  private destVisible = true;
  private hotelVisible = true;
  private fitted = false;

  constructor() {
    // Re-dibuja marcadores cuando llegan los datos (async) — mismo patrón
    // que competitive-map. Cubre el caso de hoteles que arriban después
    // de los destinos.
    effect(() => {
      this.destinations();
      this.hotels();
      if (this.map && this.map.loaded()) this.redrawMarkers();
    });
    this.destroyRef.onDestroy(() => {
      this.clearMarkers();
      this.map?.remove();
      this.map = null;
    });
    this.loadData();
  }

  ngAfterViewInit(): void {
    this.initMap();
  }

  private loadData() {
    this.api.getGeoDestinations().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (dests) => {
        this.destinations.set(dests);
        this.loaded.set(true);
      },
    });
    this.api.getGeoHotels().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (hotels) => this.hotels.set(hotels),
    });
  }

  private initMap() {
    if (this.map) return;
    const el = this.mapContainer().nativeElement;

    this.map = new maplibregl.Map({
      container: el,
      style: mapTileStyleUrl(),
      center: [0, 20],
      zoom: 2,
      attributionControl: false,
    });

    this.map.addControl(new maplibregl.NavigationControl(), 'top-right');
    this.map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left');

    this.map.on('load', () => this.redrawMarkers());
  }

  private redrawMarkers() {
    if (!this.map) return;
    this.clearMarkers();

    for (const d of this.destinations()) {
      if (d.latitude === null || d.longitude === null) continue;
      const marker = this.makeMarker([d.longitude, d.latitude], 'location_on', '#1463ff', 'Destino turístico')
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(`
            <div style="font-family:sans-serif; min-width:180px">
              <strong style="font-size:1rem">${d.visibleName || d.destinationDisplayName}</strong>
              ${d.country ? `<br><span style="color:#64748b">${d.country}${d.city ? `, ${d.city}` : ''}</span>` : ''}
              <br><span style="color:#94a3b8;font-size:0.8rem">Destino #${d.srchDestinationId}</span>
              <br><a href="/admin/destinations/${d.srchDestinationId}" style="color:#1463ff;font-size:0.8rem">Editar destino →</a>
            </div>
          `),
        )
        .addTo(this.map);
      if (!this.destVisible) marker.remove();
      this.destMarkers.push(marker);
    }

    for (const h of this.hotels()) {
      if (h.latitude === null || h.longitude === null) continue;
      const stars = h.stars ? '★'.repeat(Math.min(h.stars, 5)) : '';
      const marker = this.makeMarker([h.longitude, h.latitude], 'hotel', '#059669', 'Hotel')
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(`
            <div style="font-family:sans-serif; min-width:180px">
              <strong>${h.displayName || h.hotelName}</strong>
              ${stars ? `<br>${stars}` : ''}
              ${h.reviewScore ? `<br><span style="color:#eab308">★ ${h.reviewScore.toFixed(1)}</span>` : ''}
              <br><span style="color:#94a3b8;font-size:0.8rem">Hotel #${h.propId}</span>
              ${h.destinationDisplayName ? `<br><span style="color:#64748b;font-size:0.8rem">${h.destinationDisplayName}</span>` : ''}
            </div>
          `),
        )
        .addTo(this.map);
      if (!this.hotelVisible) marker.remove();
      this.hotelMarkers.push(marker);
    }

    if (!this.fitted) {
      const bounds = new maplibregl.LngLatBounds();
      let points = 0;
      for (const d of this.destinations()) {
        if (d.latitude === null || d.longitude === null) continue;
        bounds.extend([d.longitude, d.latitude]);
        points++;
      }
      if (points > 1) {
        this.map.fitBounds(bounds, { padding: 30, duration: 0 });
        this.fitted = true;
      }
    }
  }

  private makeMarker(lngLat: [number, number], symbol: string, colour: string, title: string): maplibregl.Marker {
    const el = document.createElement('div');
    el.innerHTML = `<span class="material-symbols-outlined" style="font-size:1.4rem;color:${colour}">${symbol}</span>`;
    el.title = title;
    return new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(lngLat);
  }

  private setMarkersVisible(markers: maplibregl.Marker[], visible: boolean) {
    if (!this.map) return;
    for (const m of markers) {
      if (visible) m.addTo(this.map);
      else m.remove();
    }
  }

  toggleDestinations() {
    this.destVisible = !this.destVisible;
    this.setMarkersVisible(this.destMarkers, this.destVisible);
  }

  toggleHotels() {
    this.hotelVisible = !this.hotelVisible;
    this.setMarkersVisible(this.hotelMarkers, this.hotelVisible);
  }

  private clearMarkers() {
    for (const m of this.destMarkers) m.remove();
    this.destMarkers = [];
    for (const m of this.hotelMarkers) m.remove();
    this.hotelMarkers = [];
  }
}
