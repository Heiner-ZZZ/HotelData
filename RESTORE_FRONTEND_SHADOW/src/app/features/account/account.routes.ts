import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const ACCOUNT_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'bookings'
  },
  {
    path: 'bookings',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Mis reservas',
      description:
        'La vista consolidada de viajes y reservas del viajero se migrara despues del flujo publico y la gestion hotelera.'
    }
  },
  {
    path: 'bookings/new',
    loadComponent: () =>
      import('../reservations/pages/reservation-new-page/reservation-new-page').then(
        (m) => m.ReservationNewPageComponent
      )
  },
  {
    path: 'bookings/:bookingId',
    loadComponent: () =>
      import('../reservations/pages/reservation-detail-page/reservation-detail-page').then(
        (m) => m.ReservationDetailPageComponent
      )
  },
  {
    path: 'profile',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Perfil del viajero',
      description:
        'Aqui quedaran preferencias, metodos de contacto y personalizacion de experiencia cuando se migre la cuenta completa.'
    }
  }
];
