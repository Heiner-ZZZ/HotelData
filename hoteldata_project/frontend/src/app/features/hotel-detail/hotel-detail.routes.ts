import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const HOTEL_DETAIL_ROUTES: Routes = [
  {
    path: ':hotelId',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Detalle de hotel',
      description: 'La estructura del detalle ya esta reservada para la siguiente fase de migracion.'
    }
  }
];
