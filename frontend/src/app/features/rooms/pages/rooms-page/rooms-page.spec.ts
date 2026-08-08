import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder } from '@angular/forms';
import { of, Subject } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { RoomsApiService } from '../../services/rooms-api.service';
import { RoomsPageComponent } from './rooms-page';

describe('RoomsPageComponent', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const propertyContext = {
      ready: signal(false),
      singleHotelMode: signal(false),
      currentPropId: signal(1),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;

    TestBed.configureTestingModule({
      imports: [RoomsPageComponent],
      providers: [
        provideHttpClient(),
        FormBuilder,
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: { queryParamMap: of({ get: () => '1' }) },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: RoomsApiService, useValue: {} },
        { provide: ToastService, useValue: { success: jest.fn(), error: jest.fn() } },
      ],
    });

    const fixture = TestBed.createComponent(RoomsPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, mode: TestBed.inject(OperationModeService) };
  }

  it('starts a new-room creation flow in insert mode and reveals the form', () => {
    const { component, mode } = setup();

    expect(component.showCreateForm()).toBe(false);
    expect(component.hasExistingRoomTypes()).toBe(false);
    expect(mode.mode()).toBe('read');

    component.startCreate('new');

    expect(component.showCreateForm()).toBe(true);
    expect(component.createMode()).toBe('new');
    expect(mode.mode()).toBe('insert');
    expect(mode.detail()).toBe('Nueva habitación');
  });

  it('starts the existing-room-type flow in insert mode and reveals the form', () => {
    const { component, mode } = setup();

    component.startCreate('existing');

    expect(component.showCreateForm()).toBe(true);
    expect(component.createMode()).toBe('existing');
    expect(mode.mode()).toBe('insert');
    expect(mode.detail()).toBe('Habitación con tipo existente');
  });

  it('updates the mode detail when switching creation strategy inside the form', () => {
    const { component, mode } = setup();

    component.startCreate('existing');
    component.setCreateMode('new');

    expect(mode.mode()).toBe('insert');
    expect(mode.detail()).toBe('Nueva habitación');

    component.setCreateMode('existing');

    expect(mode.detail()).toBe('Habitación con tipo existente');
  });
});
