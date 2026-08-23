import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { provideRouter } from '@angular/router';
import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { AuthService } from '../../../../../core/auth/auth.service';
import { GuestsPickerComponent } from '../../../../../shared/ui/guests-picker/guests-picker';
import { RnPlannerSectionComponent } from './rn-planner-section';

describe('RnPlannerSectionComponent — widgets compartidos (centralización)', () => {
  function setup() {
    const authService = {
      currentUser: signal<unknown>(null),
      isAuthenticated: signal(false),
      sessionLoaded: signal(true),
      invalidateSession: jest.fn(),
    } as unknown as AuthService;

    TestBed.configureTestingModule({
      imports: [RnPlannerSectionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AuthService, useValue: authService },
      ],
    });

    const form = new FormBuilder().nonNullable.group({
      propId: [0],
      checkInDate: [''],
      checkOutDate: [''],
      checkInTime: [''],
      checkOutTime: [''],
      adults: [2],
      children: [0],
      rooms: [1],
    });

    const fixture = TestBed.createComponent(RnPlannerSectionComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('form', form);
    fixture.componentRef.setInput('selectedPropId', 0);
    fixture.componentRef.setInput('selectedLabel', '');
    fixture.componentRef.setInput('selectedHotel', null);
    fixture.componentRef.setInput('today', '2026-08-21');
    fixture.componentRef.setInput('checkInDate', '');
    fixture.componentRef.setInput('checkOutDate', '');
    fixture.componentRef.setInput('adults', 2);
    fixture.componentRef.setInput('children', 0);
    fixture.componentRef.setInput('rooms', 1);
    fixture.componentRef.setInput('computedNights', 0);
    fixture.componentRef.setInput('availabilityInfo', null);
    fixture.componentRef.setInput('ratePlans', []);
    fixture.componentRef.setInput('ratePlansLoading', false);
    fixture.componentRef.setInput('selectedRatePlanId', '');
    fixture.detectChanges();
    return { fixture, component, form };
  }

  it('usa el guests-picker compartido en lugar de los mini-steppers inline', () => {
    const { fixture } = setup();

    expect(fixture.nativeElement.querySelector('app-guests-picker')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.mini-stepper')).toBeNull();
  });

  it('mantiene el calendario compartido y el selector de hotel', () => {
    const { fixture } = setup();

    expect(fixture.nativeElement.querySelector('app-date-range-picker')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('app-property-selector')).not.toBeNull();
  });

  it('propaga el cambio de huéspedes al output adjust como delta', () => {
    const { fixture, component } = setup();
    const adjustSpy = jest.fn();
    component.adjust.subscribe(adjustSpy);

    const picker = fixture.debugElement
      .query(By.directive(GuestsPickerComponent))
      .componentInstance as GuestsPickerComponent;
    picker.adjust('adults', 1); // 2 → 3

    expect(adjustSpy).toHaveBeenCalledWith({ field: 'adults', delta: 1 });
  });
});
