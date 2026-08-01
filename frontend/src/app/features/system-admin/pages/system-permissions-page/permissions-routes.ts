import { Routes } from '@angular/router';

import { PermissionsCatalogPageComponent } from './permissions-catalog-page';
import { PermissionsMatrixPageComponent } from './permissions-matrix-page';
import { PermissionsRolesPageComponent } from './permissions-roles-page';
import { RolePermissionsPageComponent } from './role-permissions-page';

export const PERMISSIONS_INTERNAL_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'matrix' },
  { path: 'matrix', component: PermissionsMatrixPageComponent },
  { path: 'roles', component: PermissionsRolesPageComponent },
  { path: 'roles/:roleName', component: RolePermissionsPageComponent },
  { path: 'catalog', component: PermissionsCatalogPageComponent },
];
