import { Routes } from '@angular/router';

export const ACCOUNT_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'bookings'
  },
  {
    path: 'bookings',
    loadChildren: () =>
      import('../reservations/reservations.routes').then((m) => m.RESERVATIONS_ROUTES)
  },
  {
    path: 'bookings/:bookingId/amenities',
    loadComponent: () => import('../amenities/pages/guest-amenity-catalog-page/guest-amenity-catalog-page').then(
      (m) => m.GuestAmenityCatalogPageComponent
    )
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./pages/profile-page/profile-page').then((m) => m.ProfilePageComponent)
  },
  {
    path: 'notifications',
    loadComponent: () =>
      import('../notifications/pages/notifications-page/notifications-page').then((m) => m.NotificationsPageComponent)
  },
  {
    path: 'billing',
    loadChildren: () =>
      import('../billing/client-billing.routes').then((m) => m.CLIENT_BILLING_ROUTES)
  }
];
