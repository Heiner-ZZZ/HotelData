import { Routes } from '@angular/router';

export const EXPENSES_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full',
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/expenses-dashboard-page/expenses-dashboard-page').then(m => m.ExpensesDashboardPageComponent),
  },
  {
    path: 'invoices',
    loadComponent: () =>
      import('./pages/invoices-list-page/invoices-list-page').then(m => m.InvoicesListPageComponent),
  },
  {
    path: 'invoices/new',
    loadComponent: () =>
      import('./pages/invoice-form-page/invoice-form-page').then(m => m.InvoiceFormPageComponent),
  },
  {
    path: 'invoices/:invoiceId',
    loadComponent: () =>
      import('./pages/invoice-detail-page/invoice-detail-page').then(m => m.InvoiceDetailPageComponent),
  },
];
