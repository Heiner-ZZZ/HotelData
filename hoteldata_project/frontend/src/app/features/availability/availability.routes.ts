import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const AVAILABILITY_ROUTES: Routes = [
  {
    path: '',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Availability',
      description: 'La edicion de disponibilidad e inventario requiere revisar primero los endpoints de partner.'
    }
  }
];
