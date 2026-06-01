import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const PROPERTIES_ROUTES: Routes = [
  {
    path: '',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Properties',
      description: 'El modulo administrativo de propiedades queda preparado para la siguiente ola de migracion.'
    }
  }
];
