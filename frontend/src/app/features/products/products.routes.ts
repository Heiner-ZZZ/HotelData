import { Routes } from '@angular/router';

export const PRODUCTS_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./pages/products-list-page/products-list-page').then((m) => m.ProductsListPageComponent)
  },
  {
    path: 'reports/margin',
    loadComponent: () =>
      import('./partials/margin-report/margin-report').then((m) => m.default)
  },
  {
    path: 'reports/cogs',
    loadComponent: () =>
      import('./partials/cogs-report/cogs-report').then((m) => m.default)
  },
  {
    path: 'reports/stock-value',
    loadComponent: () =>
      import('./partials/stock-value-report/stock-value-report').then((m) => m.default)
  },
  {
    path: 'new',
    loadComponent: () =>
      import('./pages/products-form-page/products-form-page').then((m) => m.ProductsFormPageComponent)
  },
  {
    path: ':productId/edit',
    loadComponent: () =>
      import('./pages/products-form-page/products-form-page').then((m) => m.ProductsFormPageComponent)
  }
];
