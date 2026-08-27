import type { AbstractControl, FormGroup } from '@angular/forms';

/**
 * Mensajes de validación con acción para el formulario público de reservas
 * (flujo huésped). Cada helper devuelve el mensaje a mostrar (con qué hacer)
 * o `null` cuando el campo no debe mostrar error.
 *
 * Criterio (mismo que el resto de la app): describir el estado Y decir qué
 * hacer, en español, con acción concreta — nunca un error crudo del validador.
 */

/** Hotel (propId): obligatorio antes de continuar. */
export function plannerHotelError(control: AbstractControl | null): string | null {
  if (!control || !control.touched) return null;
  if (control.hasError('required') || Number(control.value) === 0) {
    return 'Elegí un hotel para continuar.';
  }
  return null;
}

/** Fechas: entrada/salida faltantes o salida no posterior a la entrada. */
export function plannerDatesError(form: FormGroup): string | null {
  const checkIn = form.get('checkInDate');
  const checkOut = form.get('checkOutDate');
  if (checkIn?.touched && checkIn.hasError('required')) {
    return 'Elegí la fecha de entrada para continuar.';
  }
  if (checkOut?.touched && checkOut.hasError('required')) {
    return 'Elegí la fecha de salida para continuar.';
  }
  if (form.errors?.['invalidStayDates']) {
    return 'La fecha de salida debe ser posterior a la de entrada. Ajustá las fechas para una estancia de al menos una noche.';
  }
  return null;
}

/** Horas de entrada/salida: obligatorias (solo se validan con fechas elegidas). */
export function plannerTimeError(control: AbstractControl | null, kind: 'in' | 'out'): string | null {
  if (!control || !control.touched) return null;
  if (control.hasError('required')) {
    return kind === 'in'
      ? 'Elegí la hora de entrada (check-in) para continuar.'
      : 'Elegí la hora de salida (check-out) para continuar.';
  }
  return null;
}

/** Ocupación: rangos de adultos / niños / habitaciones. */
export function plannerOccupancyError(control: AbstractControl | null, kind: 'adults' | 'children' | 'rooms'): string | null {
  if (!control || !control.touched) return null;
  if (control.hasError('required') || control.hasError('min')) {
    switch (kind) {
      case 'adults': return 'Ingresá al menos un adulto para continuar.';
      case 'children': return 'La cantidad de niños no puede ser negativa. Corregí el valor.';
      case 'rooms': return 'Ingresá al menos una habitación para continuar.';
    }
  }
  if (control.hasError('max')) {
    switch (kind) {
      case 'adults': return 'Máximo 20 adultos por reserva. Reducí la cantidad.';
      case 'children': return 'Máximo 10 niños por reserva. Reducí la cantidad.';
      case 'rooms': return 'Máximo 10 habitaciones por reserva. Reducí la cantidad.';
    }
  }
  return null;
}

/** Nombre del huésped (staff; en el flujo cliente viene prefijado y readonly). */
export function guestNameError(control: AbstractControl | null): string | null {
  if (!control || !control.touched) return null;
  if (control.hasError('required')) {
    return 'Ingresá el nombre del huésped para continuar.';
  }
  return null;
}

/** Correo del huésped (staff; en el flujo cliente viene prefijado y readonly). */
export function guestEmailError(control: AbstractControl | null): string | null {
  if (!control || !control.touched) return null;
  if (control.hasError('required')) {
    return 'Ingresá el correo del huésped para continuar.';
  }
  if (control.hasError('email')) {
    return 'Ingresá un correo válido (ej. nombre@dominio.com).';
  }
  return null;
}

/** Teléfono: obligatorio y con caracteres válidos — solo + permitido. */
export function guestPhoneError(control: AbstractControl | null): string | null {
  if (!control || !control.touched) return null;
  if (control.hasError('required')) {
    return 'Ingresá un teléfono de contacto para continuar.';
  }
  if (control.hasError('pattern')) {
    return 'El teléfono contiene caracteres inválidos. Usá solo números, espacios, paréntesis, puntos y el signo + al inicio. El guion - no está permitido para el teléfono.';
  }
  if (control.hasError('minlength')) {
    return 'El teléfono es demasiado corto. Ingresá al menos 7 caracteres.';
  }
  if (control.hasError('maxlength')) {
    return 'El teléfono es demasiado largo. Máximo 20 caracteres.';
  }
  return null;
}

/** Cédula / documento: obligatorio — solo - permitido. */
export function guestCedulaError(control: AbstractControl | null): string | null {
  if (!control || !control.touched) return null;
  if (control.hasError('required')) {
    return 'Ingresá la cédula o documento del huésped para continuar.';
  }
  if (control.hasError('pattern')) {
    return 'La cédula contiene caracteres inválidos. Usá solo números y guiones (-). El signo + no está permitido.';
  }
  if (control.hasError('minlength')) {
    return 'La cédula es demasiado corta. Ingresá al menos 6 caracteres.';
  }
  if (control.hasError('maxlength')) {
    return 'La cédula es demasiado larga. Máximo 20 caracteres.';
  }
  return null;
}

export type AvailabilityStatus = 'unknown' | 'has_inventory' | 'no_inventory' | 'checking' | 'no_room_types';

/**
 * Etiqueta + mensaje con acción del estado de disponibilidad de un hotel.
 * El ``message`` (con qué hacer) solo se expone cuando NO hay disponibilidad.
 */
export function availabilityInfoFor(
  status: AvailabilityStatus | null | undefined,
  apiMessage?: string,
): { label: string; icon: string; color: string; message?: string } | null {
  if (!status || status === 'unknown') return null;
  switch (status) {
    case 'checking': return { label: 'Verificando...', icon: 'sync', color: 'var(--muted-text)' };
    case 'has_inventory': return { label: 'Disponible', icon: 'check_circle', color: 'var(--success)' };
    case 'no_inventory': return { label: 'Sin disponibilidad', icon: 'error', color: 'var(--danger)', message: apiMessage };
    case 'no_room_types': return { label: 'Sin tipos de habitación', icon: 'warning', color: 'var(--warning)', message: apiMessage };
    default: return null;
  }
}
