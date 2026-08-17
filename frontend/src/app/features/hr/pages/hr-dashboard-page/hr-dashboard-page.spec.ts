import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { HrApiService } from '../../services/hr-api.service';
import type { HrDashboard } from '../../models/hr.model';
import { HrDashboardPageComponent } from './hr-dashboard-page';

const DASHBOARD: HrDashboard = {
  totalEmployees: 12,
  activeEmployees: 10,
  inactiveEmployees: 2,
  departments: 4,
  recentHires: [
    {
      id: 'emp-1',
      fullName: 'Ana Recepción',
      idDocument: '123',
      phone: '',
      email: 'ana@test.local',
      position: 'Recepcionista',
      department: 'Recepción',
      isActive: true,
      hireDate: '2026-07-01T00:00:00Z',
      createdAt: '2026-07-01T00:00:00Z',
      hasUserAccount: true,
      roleAssigned: true,
    },
  ],
};

describe('HrDashboardPageComponent', () => {
  function setup(dashboard: HrDashboard | null = DASHBOARD) {
    const hrApi = {
      getDashboard: jest.fn(() => (dashboard ? of(dashboard) : throwError(() => ({ message: 'boom' })))),
    } as unknown as HrApiService;

    TestBed.configureTestingModule({
      imports: [HrDashboardPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: HrApiService, useValue: hrApi },
      ],
    });

    const fixture = TestBed.createComponent(HrDashboardPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, hrApi };
  }

  it('renderiza los KPIs del dashboard de RRHH', () => {
    const { fixture } = setup();
    const el: HTMLElement = fixture.nativeElement;

    expect(el.querySelector('.hrd-title')?.textContent).toContain('Dashboard RRHH');
    expect(el.querySelectorAll('.hrd-kpi-card').length).toBe(4);
    expect(el.textContent).toContain('12');
    expect(el.textContent).toContain('10');
    expect(el.textContent).toContain('2');
    expect(el.textContent).toContain('4');
  });

  it('muestra las contrataciones recientes', () => {
    const { fixture } = setup();
    const el: HTMLElement = fixture.nativeElement;

    expect(el.textContent).toContain('Ana Recepción');
    expect(el.textContent).toContain('Recepcionista · Recepción');
  });

  it('cae al estado de error cuando la API falla y retry recarga', () => {
    const { fixture, hrApi } = setup(null);
    const el: HTMLElement = fixture.nativeElement;

    expect(el.querySelector('app-error-state')).toBeTruthy();
    expect(hrApi.getDashboard).toHaveBeenCalled();
  });
});
