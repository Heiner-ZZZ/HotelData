import { TestBed } from '@angular/core/testing';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { Subject } from 'rxjs';

import { OperationModeService } from './operation-mode.service';

function createRouter(routeData: Record<string, unknown> = {}) {
  const events = new Subject<unknown>();
  const deepestRoute = { data: routeData, firstChild: null };
  const rootRoute = { data: {}, firstChild: deepestRoute };
  const router = {
    url: '/management/current',
    events: events.asObservable(),
    routerState: { snapshot: { root: rootRoute } },
  } as unknown as Router;
  return { events, router };
}

describe('OperationModeService', () => {
  function setup(routeData: Record<string, unknown> = {}) {
    const { events, router } = createRouter(routeData);
    TestBed.configureTestingModule({
      providers: [
        OperationModeService,
        { provide: Router, useValue: router },
      ],
    });
    return { events, service: TestBed.inject(OperationModeService) };
  }

  it('publishes route metadata as the page mode after navigation', () => {
    const { events, service } = setup({ operationMode: 'insert', operationDetail: 'Reserva' });

    events.next(new NavigationEnd(1, '/management/recepcion', '/management/recepcion/new'));

    expect(service.mode()).toBe('insert');
    expect(service.detail()).toBe('Reserva');
    expect(service.info().label).toBe('Creando');
  });

  it('keeps the page mode when only the query string changes', () => {
    const { events, service } = setup({ operationMode: 'insert', operationDetail: 'Reserva' });

    events.next(new NavigationEnd(1, '/management/recepcion', '/management/recepcion/new'));
    events.next(new NavigationStart(2, '/management/recepcion/new?prop_id=1'));
    events.next(new NavigationEnd(2, '/management/recepcion/new?prop_id=1', '/management/recepcion/new?prop_id=1'));

    expect(service.mode()).toBe('insert');
    expect(service.detail()).toBe('Reserva');
  });

  it('overlays a transient mode and restores the page mode after cleanup', () => {
    const { events, service } = setup({ operationMode: 'update', operationDetail: 'Perfil del hotel' });
    events.next(new NavigationEnd(1, '/management/properties/1/edit', '/management/properties/1/edit'));

    const release = service.setTransientMode('delete', 'Perfil del hotel');
    expect(service.mode()).toBe('delete');
    expect(service.detail()).toBe('Perfil del hotel');

    release();

    expect(service.mode()).toBe('update');
    expect(service.detail()).toBe('Perfil del hotel');
  });

  it('does not let an old transient cleanup clear a newer transient mode', () => {
    const { service } = setup();
    const staleCleanup = service.setTransientMode('insert', 'A');
    const currentCleanup = service.setTransientMode('delete', 'B');

    staleCleanup();

    expect(service.mode()).toBe('delete');
    expect(service.detail()).toBe('B');

    currentCleanup();
    expect(service.mode()).toBe('read');
    expect(service.detail()).toBe('');
  });

  it('restores the current underlying mode when a nested transient closes', () => {
    const { service } = setup();
    const pageCleanup = service.setTransientMode('update', 'Check-in');
    const dialogCleanup = service.setTransientMode('delete', 'Confirmación');

    pageCleanup();
    expect(service.mode()).toBe('delete');

    dialogCleanup();
    expect(service.mode()).toBe('read');
  });

  it('keeps a transient mode during a query-param-only navigation', () => {
    const { events, service } = setup({ operationMode: 'read' });
    const release = service.setTransientMode('delete', 'Confirmación');

    events.next(new NavigationStart(1, '/management/current?prop_id=1'));

    expect(service.mode()).toBe('delete');
    release();
    expect(service.mode()).toBe('read');
  });

  it('clears a transient mode at the start of a real route navigation', () => {
    const { events, service } = setup({ operationMode: 'read' });
    const release = service.setTransientMode('delete', 'Confirmación');

    events.next(new NavigationStart(1, '/management/other'));
    release();

    expect(service.mode()).toBe('read');
  });
});
