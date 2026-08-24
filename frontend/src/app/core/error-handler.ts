import { ErrorHandler, Injectable } from '@angular/core';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  handleError(error: unknown): void {
    const msg = String((error as any)?.message ?? error ?? '');
    // Silencia el bug conocido de Syncfusion DatePicker con showHeaderBar=false:
    // updateMinMaxDateToEditor hace this.element.querySelector sobre undefined
    // cuando el header date-picker no está renderizado y se cambia selectedDate vía goToday.
    // No rompe la app (el Schedule sigue funcionando), solo ensucia la consola.
    if (msg.includes('querySelector') && msg.includes('updateMinMaxDateToEditor')) {
      return;
    }
    if (msg.includes('Cannot read properties of undefined') && msg.includes('querySelector')) {
      // Filtro más amplio para el mismo bug en diferentes chunks (DtWgsFJA, C6ZAB5Ld, etc.)
      // Verifica stack si existe
      const stack = String((error as any)?.stack ?? '');
      if (stack.includes('updateMinMaxDateToEditor') || stack.includes('validateDate')) {
        return;
      }
    }
    // Delega al handler por defecto (consola)
    console.error(error);
  }
}
