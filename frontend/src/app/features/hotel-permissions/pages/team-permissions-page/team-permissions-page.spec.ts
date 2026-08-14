import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { BehaviorSubject, Subject } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { TeamPermissionsPageComponent } from './team-permissions-page';

describe('TeamPermissionsPageComponent', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
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
      currentUser: signal({ username: 'admin_test' }),
    } as unknown as AuthService;

    TestBed.configureTestingModule({
      imports: [TeamPermissionsPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: { queryParamMap: queryParams.asObservable() },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: AuthService, useValue: auth },
      ],
    });

    const fixture = TestBed.createComponent(TeamPermissionsPageComponent);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    const confirmDialog = TestBed.inject(ConfirmDialogService);
    return { fixture, component: fixture.componentInstance, http, router, propertyContext, queryParams, confirmDialog };
  }

  function seedResources(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }) {
    ctx.http.expectOne('/api/management/hotels/1/roles').flush({
      items: [],
      templates: [],
      permission_codes: ['dashboard.read'],
    });
    ctx.http.expectOne('/api/management/hotels/1/assignments').flush({ assigned: [], unassigned_staff: [] });
    return new Promise<void>((resolve) => setTimeout(resolve, 0));
  }

  it('muestra el property selector en el header (slot actions), como las demás UIs de management', async () => {
    const ctx = setup();
    await seedResources(ctx);
    ctx.fixture.detectChanges();

    const selector = ctx.fixture.nativeElement.querySelector('app-property-selector');
    expect(selector).not.toBeNull();
  });

  it('al seleccionar otra propiedad actualiza el contexto y navega con el nuevo prop_id', async () => {
    const ctx = setup();
    await seedResources(ctx);

    ctx.component.onPropSelected({ propId: 2, label: 'Hotel Lima Centro' });

    expect(ctx.propertyContext.setProperty).toHaveBeenCalledWith(2, 'Hotel Lima Centro');
    expect(ctx.router.navigate).toHaveBeenCalledWith(
      [],
      expect.objectContaining({ queryParams: expect.objectContaining({ prop_id: 2 }) }),
    );
  });

  it('refetches roles y assignments cuando cambia el prop_id del contexto', async () => {
    const ctx = setup();
    await seedResources(ctx);
    ctx.fixture.detectChanges();

    ctx.propertyContext.currentPropId.set(7);
    ctx.propertyContext.currentPropLabel.set('Hotel Quito');
    ctx.fixture.detectChanges();

    ctx.http.expectOne('/api/management/hotels/7/roles').flush({
      items: [],
      templates: [],
      permission_codes: ['dashboard.read'],
    });
    ctx.http.expectOne('/api/management/hotels/7/assignments').flush({ assigned: [], unassigned_staff: [] });
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();

    expect(ctx.component.currentPropId()).toBe(7);
    expect(ctx.component.hotelLabel()).toBe('Hotel Quito');
  });
});
