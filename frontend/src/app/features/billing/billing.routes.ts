import { Routes } from '@angular/router';

export const BILLING_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'invoices',
    pathMatch: 'full',
  },
  {
    path: 'invoices',
    loadComponent: () =>
      import('./pages/invoices-list-page/invoices-list-page').then(m => m.InvoicesListPageComponent),
  },
  {
    path: 'invoices/:invoiceId',
    loadComponent: () =>
      import('./pages/invoice-detail-page/invoice-detail-page').then(m => m.InvoiceDetailPageComponent),
  },
  {
    path: 'payments',
    loadComponent: () =>
      import('./pages/payments-list-page/payments-list-page').then(m => m.PaymentsListPageComponent),
  },
];
