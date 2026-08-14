import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { ServiceRequestsDashboardPageComponent } from './service-requests-dashboard-page';

describe('ServiceRequestsDashboardPageComponent (gate de exportación)', () => {
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
    } as unknown as AuthService;

    TestBed.configureTestingModule({
      imports: [ServiceRequestsDashboardPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({ prop_id: '1', prop_label: 'Hotel Test' }) },
            queryParamMap: of(convertToParamMap({ prop_id: '1' })),
          },
        },
        { provide: AuthService, useValue: auth },
      ],
    });

    const fixture = TestBed.createComponent(ServiceRequestsDashboardPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, auth };
  }

  it('deshabilita la exportación CSV sin reports.download', () => {
    const ctx = setup(false);
    expect(ctx.component.canExport()).toBe(false);
  });

  it('habilita la exportación CSV con reports.download', () => {
    const ctx = setup(true);
    expect(ctx.component.canExport()).toBe(true);
  });

  it('consulta el permiso reports.download en hasPermission', () => {
    const ctx = setup(true);

    void ctx.component.canExport();
    expect(ctx.auth.hasPermission).toHaveBeenCalledWith('reports.download');
  });
});
