import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, inject, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import * as L from 'leaflet';

import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { GeoDestination, GeoHotel } from '../../models/map.model';
import { MapApiService } from '../../services/map-api.service';

@Component({
  selector: 'app-world-map-page',
  imports: [LoadingStateComponent, PageHeaderComponent, RouterLink],
  templateUrl: './world-map-page.html',
  styleUrl: './world-map-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorldMapPageComponent {
  private readonly api = inject(MapApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly mapContainer = viewChild.required<ElementRef<HTMLElement>>('mapContainer');
  readonly loaded = signal(false);
  readonly destinations = signal<GeoDestination[]>([]);
  readonly hotels = signal<GeoHotel[]>([]);

  private map: L.Map | null = null;
  private destLayer: L.LayerGroup | null = null;
  private hotelLayer: L.LayerGroup | null = null;

  constructor() {
    this.loadData();
  }

  private loadData() {
    this.api.getGeoDestinations().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (dests) => {
        this.destinations.set(dests);
        this.loaded.set(true);
        this.initMap();
      },
    });
    this.api.getGeoHotels().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (hotels) => this.hotels.set(hotels),
    });
  }

  private initMap() {
    if (this.map) return;
    const el = this.mapContainer().nativeElement;

    this.map = L.map(el, {
      center: [20, 0],
      zoom: 2,
      zoomControl: true,
      attributionControl: false,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      minZoom: 2,
    }).addTo(this.map);

    // Add zoom control to top-right
    L.control.zoom({ position: 'topright' }).addTo(this.map);

    this.destLayer = L.layerGroup().addTo(this.map);
    this.hotelLayer = L.layerGroup().addTo(this.map);

    // Custom icons
    const destIcon = L.divIcon({
      html: '<span style="font-size:24px">📍</span>',
      className: '',
      iconSize: [24, 24],
      iconAnchor: [12, 24],
      popupAnchor: [0, -24],
    });

    const hotelIcon = L.divIcon({
      html: '<span style="font-size:18px">🏨</span>',
      className: '',
      iconSize: [18, 18],
      iconAnchor: [9, 18],
      popupAnchor: [0, -18],
    });

    // Add destination markers
    for (const d of this.destinations()) {
      if (d.latitude === null || d.longitude === null) continue;
      const marker = L.marker([d.latitude, d.longitude], { icon: destIcon });
      marker.bindPopup(`
        <div style="font-family:sans-serif; min-width:180px">
          <strong style="font-size:1rem">${d.visibleName || d.destinationDisplayName}</strong>
          ${d.country ? `<br><span style="color:#64748b">${d.country}${d.city ? `, ${d.city}` : ''}</span>` : ''}
          <br><span style="color:#94a3b8;font-size:0.8rem">Destino #${d.srchDestinationId}</span>
          <br><a href="/admin/destinations/${d.srchDestinationId}" style="color:#1463ff;font-size:0.8rem">Editar destino →</a>
        </div>
      `);
      this.destLayer!.addLayer(marker);
    }

    // Add hotel markers
    for (const h of this.hotels()) {
      if (h.latitude === null || h.longitude === null) continue;
      const stars = h.stars ? '⭐'.repeat(Math.min(h.stars, 5)) : '';
      const marker = L.marker([h.latitude, h.longitude], { icon: hotelIcon });
      marker.bindPopup(`
        <div style="font-family:sans-serif; min-width:180px">
          <strong>${h.displayName || h.hotelName}</strong>
          ${stars ? `<br>${stars}` : ''}
          ${h.reviewScore ? `<br><span style="color:#eab308">★ ${h.reviewScore.toFixed(1)}</span>` : ''}
          <br><span style="color:#94a3b8;font-size:0.8rem">Hotel #${h.propId}</span>
          ${h.destinationDisplayName ? `<br><span style="color:#64748b;font-size:0.8rem">${h.destinationDisplayName}</span>` : ''}
        </div>
      `);
      this.hotelLayer!.addLayer(marker);
    }

    // Fit bounds to show all markers
    const allBounds = this.destinations()
      .filter(d => d.latitude !== null && d.longitude !== null)
      .map(d => L.latLng(d.latitude!, d.longitude!));
    if (allBounds.length > 1) {
      this.map.fitBounds(L.latLngBounds(allBounds), { padding: [30, 30] });
    }
  }

  toggleDestinations() {
    if (this.destLayer && this.map?.hasLayer(this.destLayer)) {
      this.map.removeLayer(this.destLayer);
    } else if (this.destLayer) {
      this.destLayer.addTo(this.map!);
    }
  }

  toggleHotels() {
    if (this.hotelLayer && this.map?.hasLayer(this.hotelLayer)) {
      this.map.removeLayer(this.hotelLayer);
    } else if (this.hotelLayer) {
      this.hotelLayer.addTo(this.map!);
    }
  }
}
