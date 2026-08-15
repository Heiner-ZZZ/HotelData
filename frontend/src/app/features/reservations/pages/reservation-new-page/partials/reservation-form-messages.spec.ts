import { FormBuilder, FormControl, Validators } from '@angular/forms';

import {
  availabilityInfoFor,
  guestCedulaError,
  guestEmailError,
  guestNameError,
  guestPhoneError,
  plannerDatesError,
  plannerHotelError,
  plannerOccupancyError,
  plannerTimeError,
} from './reservation-form-messages';

describe('reservation-form-messages (mensajes con acción — flujo huésped)', () => {
  describe('plannerHotelError', () => {
    it('no muestra nada si el campo no fue tocado', () => {
      const c = new FormControl(0, [Validators.required]);
      expect(plannerHotelError(c)).toBeNull();
    });

    it('dice elegir un hotel cuando está tocado y vacío', () => {
      const c = new FormControl(0, [Validators.required]);
      c.markAsTouched();
      expect(plannerHotelError(c)).toContain('Elegí un hotel');
    });

    it('no muestra nada cuando hay hotel seleccionado', () => {
      const c = new FormControl(1);
      c.markAsTouched();
      expect(plannerHotelError(c)).toBeNull();
    });
  });

  describe('plannerDatesError', () => {
    function form(overrides: { checkIn?: string; checkOut?: string; touched?: boolean; invalidStay?: boolean }) {
      const fb = new FormBuilder();
      const f = fb.group({
        checkInDate: ['', [Validators.required]],
        checkOutDate: ['', [Validators.required]],
      }, { validators: (g) => {
        const cin = g.get('checkInDate')?.value as string;
        const cout = g.get('checkOutDate')?.value as string;
        if (cin && cout && cout <= cin) return { invalidStayDates: true };
        return null;
      } });
      f.patchValue({ checkInDate: overrides.checkIn ?? '', checkOutDate: overrides.checkOut ?? '' });
      if (overrides.touched) f.markAllAsTouched();
      if (overrides.invalidStay && overrides.checkIn && overrides.checkOut) {
        f.get('checkInDate')!.markAsTouched();
        f.get('checkOutDate')!.markAsTouched();
      }
      return f;
    }

    it('no muestra nada sin tocar los campos', () => {
      expect(plannerDatesError(form({}))).toBeNull();
    });

    it('pide la fecha de entrada cuando falta', () => {
      expect(plannerDatesError(form({ checkOut: '2026-08-20', touched: true }))).toContain('Elegí la fecha de entrada');
    });

    it('pide la fecha de salida cuando falta', () => {
      expect(plannerDatesError(form({ checkIn: '2026-08-15', touched: true }))).toContain('Elegí la fecha de salida');
    });

    it('explica ajustar las fechas cuando la salida no es posterior a la entrada', () => {
      expect(plannerDatesError(form({ checkIn: '2026-08-20', checkOut: '2026-08-15', invalidStay: true }))).toContain(
        'La fecha de salida debe ser posterior a la de entrada',
      );
    });

    it('no muestra nada con fechas válidas', () => {
      expect(plannerDatesError(form({ checkIn: '2026-08-15', checkOut: '2026-08-20', touched: true }))).toBeNull();
    });
  });

  describe('plannerTimeError', () => {
    it('pide la hora de entrada', () => {
      const c = new FormControl('', [Validators.required]);
      c.markAsTouched();
      expect(plannerTimeError(c, 'in')).toContain('Elegí la hora de entrada');
    });

    it('pide la hora de salida', () => {
      const c = new FormControl('', [Validators.required]);
      c.markAsTouched();
      expect(plannerTimeError(c, 'out')).toContain('Elegí la hora de salida');
    });

    it('no muestra nada si la hora está cargada o el campo no fue tocado', () => {
      expect(plannerTimeError(new FormControl('', [Validators.required]), 'in')).toBeNull();
      expect(plannerTimeError(new FormControl('15:00'), 'in')).toBeNull();
    });
  });

  describe('plannerOccupancyError', () => {
    it('pide al menos un adulto', () => {
      const c = new FormControl(0, [Validators.required, Validators.min(1)]);
      c.markAsTouched();
      expect(plannerOccupancyError(c, 'adults')).toContain('Ingresá al menos un adulto');
    });

    it('pide al menos una habitación', () => {
      const c = new FormControl(0, [Validators.required, Validators.min(1)]);
      c.markAsTouched();
      expect(plannerOccupancyError(c, 'rooms')).toContain('Ingresá al menos una habitación');
    });

    it('limita el máximo de adultos', () => {
      const c = new FormControl(25, [Validators.max(20)]);
      c.markAsTouched();
      expect(plannerOccupancyError(c, 'adults')).toContain('Máximo 20 adultos');
    });

    it('limita el máximo de niños', () => {
      const c = new FormControl(12, [Validators.max(10)]);
      c.markAsTouched();
      expect(plannerOccupancyError(c, 'children')).toContain('Máximo 10 niños');
    });

    it('no muestra nada dentro de rango', () => {
      const c = new FormControl(2, [Validators.required, Validators.min(1), Validators.max(20)]);
      c.markAsTouched();
      expect(plannerOccupancyError(c, 'adults')).toBeNull();
    });
  });

  describe('guestNameError / guestEmailError', () => {
    it('pide el nombre del huésped', () => {
      const c = new FormControl('', [Validators.required]);
      c.markAsTouched();
      expect(guestNameError(c)).toContain('Ingresá el nombre del huésped');
    });

    it('pide el correo cuando falta', () => {
      const c = new FormControl('', [Validators.required, Validators.email]);
      c.markAsTouched();
      expect(guestEmailError(c)).toContain('Ingresá el correo del huésped');
    });

    it('pide un correo válido con ejemplo', () => {
      const c = new FormControl('no-es-email', [Validators.required, Validators.email]);
      c.markAsTouched();
      expect(guestEmailError(c)).toContain('nombre@dominio.com');
    });
  });

  describe('guestPhoneError / guestCedulaError', () => {
    it('pide un teléfono de contacto', () => {
      const c = new FormControl('', [Validators.required]);
      c.markAsTouched();
      expect(guestPhoneError(c)).toContain('Ingresá un teléfono de contacto');
    });

    it('explica los caracteres permitidos en el teléfono', () => {
      const c = new FormControl('abc', [Validators.required, Validators.pattern(/^[\d\s\-+().]+$/)]);
      c.markAsTouched();
      expect(guestPhoneError(c)).toContain('caracteres inválidos');
    });

    it('pide la cédula o documento', () => {
      const c = new FormControl('', [Validators.required]);
      c.markAsTouched();
      expect(guestCedulaError(c)).toContain('Ingresá la cédula o documento');
    });
  });

  describe('availabilityInfoFor (mensaje con acción de disponibilidad)', () => {
    it('no muestra nada cuando el estado es desconocido o no fue consultado', () => {
      expect(availabilityInfoFor(undefined)).toBeNull();
      expect(availabilityInfoFor('unknown')).toBeNull();
      expect(availabilityInfoFor(null)).toBeNull();
    });

    it('muestra Disponible sin mensaje de error', () => {
      const info = availabilityInfoFor('has_inventory', '1 habitación(es) disponible(s) en las fechas seleccionadas.');
      expect(info?.label).toBe('Disponible');
      expect(info?.message).toBeUndefined();
    });

    it('muestra Sin disponibilidad con el mensaje del backend (que lleva acción)', () => {
      const info = availabilityInfoFor('no_inventory', 'Sin disponibilidad en las fechas seleccionadas. Probá con otras fechas o elegí otro hotel.');
      expect(info?.label).toBe('Sin disponibilidad');
      expect(info?.icon).toBe('error');
      expect(info?.message).toContain('Probá con otras fechas o elegí otro hotel');
    });

    it('muestra Sin tipos de habitación con el mensaje de contacto a recepción', () => {
      const info = availabilityInfoFor('no_room_types', 'El hotel no tiene tipos de habitación configurados. Contactá a recepción para reservar.');
      expect(info?.label).toBe('Sin tipos de habitación');
      expect(info?.message).toContain('Contactá a recepción');
    });
  });
});
