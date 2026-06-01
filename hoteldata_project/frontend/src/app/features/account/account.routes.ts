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
    loadChildren: () =>
      import('../reservations/reservations.routes').then((m) => m.RESERVATIONS_ROUTES)
  },
  {
    path: 'profile',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Perfil del viajero',
      description: 'Ruta preparada para preferencias, datos de contacto y documentos del viajero.'
    }
  }
];
