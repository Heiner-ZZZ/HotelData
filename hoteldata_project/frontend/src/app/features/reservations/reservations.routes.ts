import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const RESERVATIONS_ROUTES: Routes = [
  {
    path: '',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Reservas',
      description: 'La migracion del modulo de reservas se hara sobre endpoints JSON dedicados.'
    }
  }
];
