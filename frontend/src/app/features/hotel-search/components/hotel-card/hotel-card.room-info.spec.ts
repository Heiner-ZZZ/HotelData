import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { TestBed } from '@angular/core/testing';

import { AuthService } from '../../../../core/auth/auth.service';
import { FavoritesService } from '../../../../core/favorites/favorites.service';
import { TrackingService } from '../../../../core/tracking/tracking.service';
import { HotelCardComponent } from './hotel-card';
import type { HotelSearchResult } from '../../models/hotel-search.model';

function makeHotel(overrides: Partial<HotelSearchResult> = {}): HotelSearchResult {
  return {
    id: 1,
    name: 'Hotel Lima Centro',
    displayName: 'Hotel Lima Centro',
    stars: 4,
    reviewScore: 4.6,
    imageUrl: null,
    destinationLabels: [],
    generalAmenities: [],
    matchedRoomType: { name: 'Habitacion sola VIP', maxAdults: 1, baseCapacity: 1 } as any,
    minNightlyRate: 135,
    minNightlyRateLabel: 'S/ 135.00',
    totalEstimated: 135,
    totalEstimatedLabel: 'S/ 135.00',
    availableRoomTypesCount: null,
    minAvailableRooms: 1,
    selected: false,
    ...overrides,
  };
}

describe('HotelCardComponent — TDD: room info arriba, Bueno/4.6 abajo', () => {
  function setup() {
    TestBed.configureTestingModule({
      imports: [HotelCardComponent],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        { provide: AuthService, useValue: { isAuthenticated: () => true, sessionLoaded: () => true } },
        { provide: FavoritesService, useValue: { favoriteIds: () => new Set<number>(), toggle: jest.fn() } },
        { provide: TrackingService, useValue: { trackHotelClick: jest.fn() } },
      ],
    });
    const fixture = TestBed.createComponent(HotelCardComponent);
    fixture.componentRef.setInput('hotel', makeHotel());
    fixture.componentRef.setInput('checkIn', '2026-08-24');
    fixture.componentRef.setInput('checkOut', '2026-08-25');
    fixture.detectChanges();
    return fixture;
  }

  it('la info de habitación (Habitacion sola VIP · 1 adulto) debe quedarse arriba en score-column', () => {
    const fixture = setup();
    const scoreColumn = fixture.nativeElement.querySelector('.score-column');
    expect(scoreColumn).not.toBeNull();
    const metaInScoreColumn = scoreColumn.querySelector('.score-meta');
    expect(metaInScoreColumn).not.toBeNull();
    expect(metaInScoreColumn.textContent).toContain('Habitacion sola VIP');
    expect(metaInScoreColumn.textContent).toContain('1 adulto');
  });

  it('el número 4.6 y descripción Bueno deben estar abajo en copy-column debajo de Ver más/Comparar', () => {
    const fixture = setup();
    const copyColumn = fixture.nativeElement.querySelector('.copy-column');
    expect(copyColumn).not.toBeNull();
    const scoreInline = copyColumn.querySelector('.score-head--inline');
    expect(scoreInline).not.toBeNull();
    expect(scoreInline.textContent).toContain('Bueno');
    const badge = scoreInline.querySelector('.score-badge');
    expect(badge).not.toBeNull();
    expect(badge.textContent).toContain('4.6');
    // Verificar orden: inline-links antes que score-head--inline en copy-column
    const children = [...copyColumn.children];
    const inlineIdx = children.findIndex((el: Element) => el.classList.contains('inline-links'));
    const scoreIdx = children.findIndex((el: Element) => el.classList.contains('score-head--inline'));
    expect(inlineIdx).toBeGreaterThan(-1);
    expect(scoreIdx).toBeGreaterThan(-1);
    expect(scoreIdx).toBeGreaterThan(inlineIdx);
    // Y que score-meta NO esté en copy-column (debe estar arriba en score-column)
    const metaInCopy = copyColumn.querySelector('.score-head--inline .score-meta');
    expect(metaInCopy).toBeNull();
  });
});
