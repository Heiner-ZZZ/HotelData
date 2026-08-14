import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { HorizontalSubNavComponent } from './horizontal-sub-nav';

const NAV_PAYLOAD = {
  items: [
    { slug: 'gestion.reservas.informes', parentSlug: 'gestion.reservas', position: 30, nodeType: 'container', label: 'Informes', href: null, icon: 'monitoring', visible: true, permissionCode: 'reports.tactical.read', horizontalMenu: true },
    { slug: 'gestion.reservas.informes.adr', parentSlug: 'gestion.reservas.informes', position: 10, nodeType: 'leaf', label: 'Dashboard ADR', href: '/management/rates/dashboard', icon: 'monitoring', visible: true, permissionCode: 'reports.rates.adr.read' },
    { slug: 'gestion.reservas.informes.calendario', parentSlug: 'gestion.reservas.informes', position: 20, nodeType: 'leaf', label: 'Calendario Tarifas', href: '/management/rates/calendar', icon: 'calendar_month', visible: true, permissionCode: 'reports.rates.calendar.read' },
    { slug: 'gestion.reservas.informes.solicitudes', parentSlug: 'gestion.reservas.informes', position: 30, nodeType: 'leaf', label: 'Dashboard Solicitudes', href: '/management/service-requests', icon: 'room_service', visible: false, permissionCode: 'reports.requests.read' },
  ],
};

describe('HorizontalSubNavComponent', () => {
  function setup(activeSlug: string) {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;

    TestBed.configureTestingModule({
      imports: [HorizontalSubNavComponent],
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
      ],
    });

    const fixture = TestBed.createComponent(HorizontalSubNavComponent);
    fixture.componentRef.setInput('activeSlug', activeSlug);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/admin/navigation').flush(NAV_PAYLOAD);

    return { fixture, component: fixture.componentInstance, http };
  }

  const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

  it('lista los hermanos visibles del informe activo, ordenados por posición, sin el container', async () => {
    const { component, fixture, http } = setup('gestion.reservas.informes.adr');
    await flush();
    fixture.detectChanges();

    expect(component.items()).toEqual([
      { label: 'Dashboard ADR', href: '/management/rates/dashboard', icon: 'monitoring' },
      { label: 'Calendario Tarifas', href: '/management/rates/calendar', icon: 'calendar_month' },
    ]);
    http.verify();
  });

  it('excluye las hojas ocultas (visible=false) por permisos', async () => {
    const { component, fixture, http } = setup('gestion.reservas.informes.calendario');
    await flush();
    fixture.detectChanges();

    const hrefs = component.items().map((i) => i.href);
    expect(hrefs).toEqual(['/management/rates/dashboard', '/management/rates/calendar']);
    expect(hrefs).not.toContain('/management/service-requests');
    http.verify();
  });

  it('acepta el slug del container y lista sus hijos visibles', async () => {
    const { component, fixture, http } = setup('gestion.reservas.informes');
    await flush();
    fixture.detectChanges();

    expect(component.items().length).toBe(2);
    http.verify();
  });
});
