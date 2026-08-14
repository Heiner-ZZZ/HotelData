import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { LedgerPageComponent } from './ledger-page';

describe('LedgerPageComponent (gate de exportación)', () => {
  function setup(hasDownload: boolean) {
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
    } as unknown as AuthService;
    const propertyContext = {
      currentPropId: signal(0),
      currentPropLabel: signal(''),
      currentPropLabelShort: signal(''),
      currentCurrency: signal('USD'),
      currentAcceptedCurrencies: signal(['USD']),
      defaultPropId: signal(0),
      mode: signal<'all' | 'single' | 'multi' | 'none'>('all'),
      assignedProperties: signal<{ propId: number; label: string }[]>([]),
      ready: signal(false),
      singleHotelMode: signal(false),
      setProperty: jest.fn(),
      clear: jest.fn(),
      reload: jest.fn(),
      setCurrency: jest.fn(),
    } as unknown as PropertyContextService;

    TestBed.configureTestingModule({
      imports: [LedgerPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
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

    const fixture = TestBed.createComponent(LedgerPageComponent);
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
