import { bootstrapApplication } from '@angular/platform-browser';
import { registerLicense } from '@syncfusion/ej2-base';

import { getRuntimeConfig } from './app/core/config/runtime-config';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import './app/core/patches/syncfusion-datepicker.patch';

const syncfusionLicenseKey = getRuntimeConfig().syncfusionLicenseKey;
if (syncfusionLicenseKey) {
  registerLicense(syncfusionLicenseKey);
}

// Silencia el bug de Syncfusion DatePicker (updateMinMaxDateToEditor querySelector)
// a nivel window, antes de que Angular lo loguee como ERROR. No afecta funcionalidad.
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    const msg = String((event as any)?.message ?? '');
    const stack = String((event as any)?.error?.stack ?? '');
    if ((msg.includes('querySelector') && msg.includes('updateMinMaxDateToEditor')) ||
        (stack.includes('updateMinMaxDateToEditor') && stack.includes('validateDate'))) {
      event.preventDefault();
    }
  });
  window.addEventListener('unhandledrejection', (event) => {
    const reason = String((event as any)?.reason?.message ?? (event as any)?.reason ?? '');
    if (reason.includes('querySelector') && reason.includes('updateMinMaxDateToEditor')) {
      event.preventDefault();
    }
  });
}

bootstrapApplication(App, appConfig).catch((error) => console.error(error));
