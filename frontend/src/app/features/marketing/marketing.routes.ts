import { Routes } from '@angular/router';

export const MARKETING_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/promotions-page/promotions-page').then((m) => m.PromotionsPageComponent)
  }
];
