import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { GuestAmenityService } from '../../../amenities/services/guest-amenity.service';
import { ReservationsApiService } from '../../services/reservations-api.service';
import { ReservationsAuthService } from '../../services/reservations-auth.service';
import { ReservationNewPageComponent } from './reservation-new-page';

describe('ReservationNewPageComponent — peticiones especiales activas', () => {
  function setup() {
    const authService = {
      currentUser: signal<unknown>(null),
      isAuthenticated: signal(false),
      sessionLoaded: signal(true),
      invalidateSession: jest.fn(),
    } as unknown as AuthService;

    TestBed.configureTestingModule({
      imports: [ReservationNewPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({ prop_id: '0' }) } },
        },
        { provide: AuthService, useValue: authService },
        ReservationsAuthService,
        {
          provide: ReservationsApiService,
          useValue: { searchUsers: jest.fn() } as unknown as ReservationsApiService,
        },
        { provide: GuestAmenityService, useValue: {} as GuestAmenityService },
        { provide: OperationModeService, useValue: {} as OperationModeService },
      ],
    });

    const fixture = TestBed.createComponent(ReservationNewPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance };
  }

  it('no ofrece peticiones cuando el catálogo activo del hotel está vacío (todas eliminadas)', () => {
    const { component } = setup();
    component.specialRequestsCatalog.set([]);
    expect(component.specialRequestOptions()).toEqual([]);
  });

  it('renderiza el selector global y elimina el select local de hoteles', () => {
    const { fixture } = setup();

    expect(fixture.nativeElement.querySelector('app-property-selector')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('select[formcontrolname="propId"]')).toBeNull();
  });

  it('usa el evento del selector global como única fuente para el hotel elegido', () => {
    const { component } = setup();

    // The real Router would try to resolve the (mock) ActivatedRoute relative
    // to empty commands; spy on navigate so the unit test asserts the signal
    // side effects without exercising URL serialization.
    jest.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

    component.onPropertySelected({ propId: 2, label: 'Resort Cancún Playa' });

    expect(component.form.controls.propId.value).toBe(2);
    expect(component.selectedPropId()).toBe(2);
    expect(component.selectedHotel()).toEqual({ propId: 2, label: 'Resort Cancún Playa' });
  });

  it('ofrece solo las peticiones activas devueltas por el catálogo del hotel', () => {
    const { component } = setup();
    component.specialRequestsCatalog.set([
      {
        label: 'Cuna para bebé', unit_price: 10, chargeable: true,
        pet_related: false, high_floor: false, late_arrival: false,
      },
      {
        label: 'Llegada tarde', unit_price: 0, chargeable: false,
        pet_related: false, high_floor: false, late_arrival: true,
      },
    ]);
    const options = component.specialRequestOptions();
    expect(options.map((o) => o.value)).toEqual(['Cuna para bebé', 'Llegada tarde']);
    expect(options.some((o) => o.value === 'Cama extra')).toBe(false);
  });
});
