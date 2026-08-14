import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { ReviewsApiService } from '../../services/reviews-api.service';
import { ReputationDashboardPageComponent } from './reputation-dashboard-page';

describe('ReputationDashboardPageComponent (gate de exportación)', () => {
  function setup(hasDownload: boolean) {
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
    } as unknown as AuthService;
    const reviewsApi = {
      getReputationAnalytics: jest.fn(() => of({ available: false, days: 30, rows: [], message: '' })),
      getReputationDashboard: jest.fn(() => of({ totalReviews: 0 })),
    } as unknown as ReviewsApiService;

    TestBed.configureTestingModule({
      imports: [ReputationDashboardPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: auth },
        { provide: ReviewsApiService, useValue: reviewsApi },
      ],
    });

    const fixture = TestBed.createComponent(ReputationDashboardPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, auth };
  }

  it('oculta los botones de exportar sin reports.download', () => {
    const ctx = setup(false);

    expect(ctx.component.canExport()).toBe(false);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).not.toContain('Exportar PDF');
    expect(el.textContent).not.toContain('Exportar Excel');
  });

  it('muestra los botones de exportar con reports.download', () => {
    const ctx = setup(true);

    expect(ctx.component.canExport()).toBe(true);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Exportar PDF');
    expect(el.textContent).toContain('Exportar Excel');
  });

  it('consulta el permiso reports.download en hasPermission', () => {
    const ctx = setup(true);

    void ctx.component.canExport();
    expect(ctx.auth.hasPermission).toHaveBeenCalledWith('reports.download');
  });
});
