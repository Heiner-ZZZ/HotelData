import { Routes } from '@angular/router';

export const CLIENT_BILLING_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/client-invoices-list-page/client-invoices-list-page').then((m) => m.ClientInvoicesListPageComponent),
  },
  {
    path: ':invoiceId',
    loadComponent: () =>
      import('./pages/client-invoice-detail-page/client-invoice-detail-page').then((m) => m.ClientInvoiceDetailPageComponent),
  },
];
