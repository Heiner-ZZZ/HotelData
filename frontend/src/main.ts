import { bootstrapApplication } from '@angular/platform-browser';
import { registerLicense } from '@syncfusion/ej2-base';

import { getRuntimeConfig } from './app/core/config/runtime-config';
import { appConfig } from './app/app.config';
import { App } from './app/app';

const syncfusionLicenseKey = getRuntimeConfig().syncfusionLicenseKey;
if (syncfusionLicenseKey) {
  registerLicense(syncfusionLicenseKey);
}

bootstrapApplication(App, appConfig).catch((error) => console.error(error));
