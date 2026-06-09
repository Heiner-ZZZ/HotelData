import { Routes } from '@angular/router';

export const POLICIES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/policies-page/policies-page').then((m) => m.PoliciesPageComponent)
  }
];
