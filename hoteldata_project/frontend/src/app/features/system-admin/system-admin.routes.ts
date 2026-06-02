import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';
import { SystemPermissionsPageComponent } from './pages/system-permissions-page/system-permissions-page';
import { SystemUsersPageComponent } from './pages/system-users-page/system-users-page';

export const SYSTEM_ADMIN_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'users'
  },
  {
    path: 'users',
    component: SystemUsersPageComponent
  },
  {
    path: 'permissions',
    component: SystemPermissionsPageComponent
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
