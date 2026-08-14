import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { HrApiService } from '../../services/hr-api.service';
import { HrAuthService } from '../../services/hr-auth.service';
import { EmployeeListPageComponent } from './employee-list-page';

describe('EmployeeListPageComponent', () => {
  function setup() {
    const queryParams = new BehaviorSubject(convertToParamMap({ prop_id: '1' }));
    const propertyContext = {
      currentPropId: signal(1),
      currentPropLabel: signal('Hotel Test'),
      currentPropLabelShort: signal('Hotel Test'),
      ready: signal(true),
      singleHotelMode: signal(false),
      mode: signal<'all' | 'single' | 'multi' | 'none'>('all'),
      assignedProperties: signal([] as { propId: number; label: string }[]),
      defaultPropId: signal(0),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;
    const auth = {
      hasPermission: jest.fn(() => true),
    } as unknown as AuthService;
    const hrAuth = {
      canOnboard: signal(true),
      canViewDirectory: signal(true),
      canManageDirectory: signal(true),
    } as unknown as HrAuthService;
    const hrApi = {
      getDepartments: jest.fn(() => of([])),
      getEmployees: jest.fn(() => of({
        items: [], total: 0, page: 1, pageSize: 20, totalPages: 1, hasNext: false, hasPrev: false,
      })),
    } as unknown as HrApiService;

    TestBed.configureTestingModule({
      imports: [EmployeeListPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        // Router real para que el RouterLink genere href (el mock no computa
        // el atributo); el ActivatedRoute mock sigue ganando para queryParams.
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParams.asObservable() } },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: AuthService, useValue: auth },
        { provide: HrAuthService, useValue: hrAuth },
        { provide: HrApiService, useValue: hrApi },
      ],
    });

    const fixture = TestBed.createComponent(EmployeeListPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, http: TestBed.inject(HttpTestingController), hrApi, propertyContext };
  }

  function seedEmployees(ctx: { hrApi: { getEmployees: jest.Mock }; fixture: { detectChanges(): void }; component: EmployeeListPageComponent }, employees: unknown[]) {
    ctx.hrApi.getEmployees.mockReturnValue(
      of({
        items: employees,
        total: employees.length,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        hasNext: false,
        hasPrev: false,
      }),
    );
    // El ngOnInit ya corrió en setup() con el mock vacío: recargar para
    // que el componente consuma la respuesta sembrada.
    ctx.component.loadEmployees();
    ctx.fixture.detectChanges();
    return new Promise<void>((resolve) => setTimeout(resolve, 0));
  }

  it('muestra un badge de cuenta activa cuando el empleado tiene user_id vivo', async () => {
    const ctx = setup();
    await seedEmployees(ctx, [{
      id: 'E1',
      fullName: 'Carlos Mendoza',
      idDocument: 'ID-1',
      phone: '',
      email: 'carlos@test.com',
      position: 'Mantenimiento',
      department: 'Mantenimiento',
      isActive: true,
      hireDate: '',
      createdAt: '',
      hasUserAccount: true,
      roleAssigned: false,
    }]);

    ctx.fixture.detectChanges();
    const el = ctx.fixture.nativeElement as HTMLElement;
    const text = el.textContent ?? '';
    expect(text).toContain('Con cuenta');
    expect(text).not.toContain('Sin cuenta');
  });

  it('muestra el estado del rol y un enlace a Team Permissions del hotel', async () => {
    const ctx = setup();
    await seedEmployees(ctx, [{
      id: 'E1',
      fullName: 'Carlos Mendoza',
      idDocument: 'ID-1',
      phone: '',
      email: 'carlos@test.com',
      position: 'Mantenimiento',
      department: 'Mantenimiento',
      isActive: true,
      hireDate: '',
      createdAt: '',
      hasUserAccount: true,
      roleAssigned: true,
    }]);

    ctx.fixture.detectChanges();
    const el = ctx.fixture.nativeElement as HTMLElement;
    const text = el.textContent ?? '';
    expect(text).toContain('Con rol');
    const link = el.querySelector('a[href*="team-permissions"]') as HTMLAnchorElement;
    expect(link).not.toBeNull();
    expect(link.getAttribute('href')).toContain('prop_id');
  });

  it('marca al empleado sin cuenta como Sin cuenta', async () => {
    const ctx = setup();
    await seedEmployees(ctx, [{
      id: 'E1',
      fullName: 'María Gómez',
      idDocument: 'ID-2',
      phone: '',
      email: 'maria@test.com',
      position: 'Recepcionista',
      department: 'Recepción',
      isActive: true,
      hireDate: '',
      createdAt: '',
      hasUserAccount: false,
      roleAssigned: false,
    }]);

    ctx.fixture.detectChanges();
    const text = ctx.fixture.nativeElement.textContent ?? '';
    expect(text).toContain('Sin cuenta');
  });

  it('el enlace a Team Permissions usa el prop_id actual del contexto', async () => {
    const ctx = setup();
    await seedEmployees(ctx, [{
      id: 'E1',
      fullName: 'Carlos Mendoza',
      idDocument: 'ID-1',
      phone: '',
      email: 'carlos@test.com',
      position: 'Mantenimiento',
      department: 'Mantenimiento',
      isActive: true,
      hireDate: '',
      createdAt: '',
      hasUserAccount: true,
      roleAssigned: true,
    }]);

    ctx.propertyContext.currentPropId.set(7);
    ctx.fixture.detectChanges();
    const link = (ctx.fixture.nativeElement as HTMLElement).querySelector('a[href*="team-permissions"]') as HTMLAnchorElement;
    expect(link).not.toBeNull();
    expect(link.getAttribute('href')).toContain('prop_id=7');
  });
});
