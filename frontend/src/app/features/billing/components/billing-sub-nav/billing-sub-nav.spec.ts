import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { BillingSubNavComponent } from './billing-sub-nav';

function setup(permissions: string[]) {
  const auth = { hasPermission: jest.fn((p: string) => permissions.includes(p)) } as unknown as AuthService;

  TestBed.configureTestingModule({
    imports: [BillingSubNavComponent],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([{ path: 'management/billing/payments', component: BillingSubNavComponent }]),
      { provide: AuthService, useValue: auth },
    ],
  });

  const fixture = TestBed.createComponent(BillingSubNavComponent);
  fixture.detectChanges();
  return { fixture, auth };
}

function labels(el: HTMLElement): string[] {
  return [...el.querySelectorAll('.billing-sub-nav-link')].map((l) =>
    l.querySelector('.billing-nav-label')?.textContent?.trim() ?? '',
  );
}

describe('BillingSubNavComponent', () => {
  it('muestra solo los botones cuyo permiso tiene el usuario', () => {
    const { fixture } = setup(['billing.read', 'payments.read']);
    const el = fixture.nativeElement as HTMLElement;

    expect(labels(el)).toEqual(['Facturas', 'Pagos']);
  });

  it('muestra los 4 botones cuando el usuario tiene todos los permisos', () => {
    const { fixture } = setup([
      'reports.billing.invoices.read',
      'reports.billing.payments.read',
      'billing.read',
      'payments.read',
    ]);
    const el = fixture.nativeElement as HTMLElement;

    expect(labels(el)).toEqual(['Dashboard', 'Dashboard Pagos', 'Facturas', 'Pagos']);
  });

  it('no renderiza el contenedor (ni su borde) si el usuario no tiene ningún permiso de facturación', () => {
    const { fixture } = setup([]);
    const el = fixture.nativeElement as HTMLElement;

    expect(el.querySelector('.billing-sub-nav')).toBeNull();
    expect(el.querySelector('nav')).toBeNull();
  });

  it('apunta cada botón a la ruta correcta de facturación', () => {
    const { fixture } = setup([
      'reports.billing.invoices.read',
      'reports.billing.payments.read',
      'billing.read',
      'payments.read',
    ]);
    const el = fixture.nativeElement as HTMLElement;

    const hrefs = [...el.querySelectorAll('.billing-sub-nav-link')].map((l) => l.getAttribute('href'));
    expect(hrefs).toEqual([
      '/management/billing/dashboard',
      '/management/billing/payments-dashboard',
      '/management/billing/invoices',
      '/management/billing/payments',
    ]);
  });

  it('marca activo el botón de la ruta actual aunque la URL tenga query params (prop_id)', async () => {
    const { fixture } = setup(['billing.read', 'payments.read']);
    const router = TestBed.inject(Router);

    await router.navigateByUrl('/management/billing/payments?prop_id=1&prop_label=Hotel%20Lima%20Centro');
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const active = el.querySelector('.billing-sub-nav-link.active');
    expect(active?.querySelector('.billing-nav-label')?.textContent?.trim()).toBe('Pagos');
  });
});
