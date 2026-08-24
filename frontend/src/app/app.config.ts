import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, ErrorHandler, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter, withInMemoryScrolling } from '@angular/router';

import { authInterceptor } from './core/auth/auth.interceptor';
import { baseUrlInterceptor } from './core/api/base-url.interceptor';
import { httpErrorInterceptor } from './core/api/http-error.interceptor';
import { transientRetryInterceptor } from './core/api/transient-retry.interceptor';
import { GlobalErrorHandler } from './core/error-handler';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    provideHttpClient(
      withInterceptors([baseUrlInterceptor, httpErrorInterceptor, transientRetryInterceptor, authInterceptor])
    ),
    provideRouter(
      routes,
      withInMemoryScrolling({
        scrollPositionRestoration: 'enabled',
        anchorScrolling: 'enabled'
      })
    )
  ]
};
