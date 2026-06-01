import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const MANAGEMENT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/dashboard-page/dashboard-page').then((m) => m.ManagementDashboardPageComponent)
  },
  {
    path: 'reservations',
    loadChildren: () =>
      import('../reservations/reservations.routes').then((m) => m.RESERVATIONS_ROUTES)
  },
  {
    path: 'properties',
    loadChildren: () =>
      import('../properties/properties.routes').then((m) => m.PROPERTIES_ROUTES)
  },
  {
    path: 'availability',
    loadChildren: () =>
      import('../availability/availability.routes').then((m) => m.AVAILABILITY_ROUTES)
  },
  {
    path: 'rooms',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Habitaciones',
      description: 'Ruta preparada para el siguiente modulo de tipos de habitacion y capacidad operativa.'
    }
  },
  {
    path: 'rates',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Tarifas',
      description: 'Ruta preparada para la siguiente ola de migracion de tarifas y calendarios.'
    }
  },
  {
    path: 'policies',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Politicas',
      description: 'Ruta preparada para politicas operativas, comerciales y de propiedad.'
    }
  },
  {
    path: 'amenities',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Amenities',
      description: 'Ruta preparada para servicios, facilidades y catalogo comercial de la propiedad.'
    }
  },
  {
    path: 'check-ins',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Check-ins',
      description: 'Ruta preparada para operacion diaria de recepcion y llegadas.'
    }
  },
  {
    path: 'check-outs',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Check-outs',
      description: 'Ruta preparada para operacion diaria de salidas y cierre de estancia.'
    }
  },
  {
    path: 'reports',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Reportes',
      description: 'Ruta preparada para ocupacion, ingresos, reservas y mercados/canales.'
    }
  },
  {
    path: 'settings',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Configuracion',
      description: 'Ruta preparada para perfil del hotel, usuarios, roles e integraciones.'
    }
  }
];
