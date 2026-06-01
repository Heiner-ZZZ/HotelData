import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const SYSTEM_ADMIN_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'users'
  },
  {
    path: 'users',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Usuarios globales',
      description: 'Ruta preparada para administracion global de usuarios del sistema.'
    }
  },
  {
    path: 'permissions',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Permisos',
      description: 'Ruta preparada para gestion global de roles, permisos y matrices de acceso.'
    }
  },
  {
    path: 'audit',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Auditoria',
      description: 'Ruta preparada para eventos de seguridad, trazabilidad y cambios globales.'
    }
  },
  {
    path: 'monitoring',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Monitoreo',
      description: 'Ruta preparada para salud de servicios, integraciones y observabilidad.'
    }
  }
];
