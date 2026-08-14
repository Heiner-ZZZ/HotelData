import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ReservationsListPageComponent } from './reservations-list-page';

describe('ReservationsListPageComponent (gate de exportación)', () => {
  function setup(hasDownload: boolean) {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
      currentUser: () => null,
    } as unknown as AuthService;
    const propertyContext = {
      currentPropId: signal(0),
      currentPropLabel: signal(''),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;

    TestBed.configureTestingModule({
      imports: [ReservationsListPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: AuthService, useValue: auth },
      ],
    });

    const fixture = TestBed.createComponent(ReservationsListPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, auth };
  }

  it('deshabilita la exportación sin reports.download', () => {
    const ctx = setup(false);
    expect(ctx.component.canExport()).toBe(false);
  });

  it('habilita la exportación con reports.download', () => {
    const ctx = setup(true);
    expect(ctx.component.canExport()).toBe(true);
  });

  it('consulta el permiso reports.download en hasPermission', () => {
    const ctx = setup(true);

    void ctx.component.canExport();
    expect(ctx.auth.hasPermission).toHaveBeenCalledWith('reports.download');
  });
});
