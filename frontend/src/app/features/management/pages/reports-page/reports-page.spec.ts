import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from '../../../../core/auth/auth.service';
import { ManagementReportsPageComponent } from './reports-page';

describe('ManagementReportsPageComponent (gate de exportación)', () => {
  function setup(hasDownload: boolean) {
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
    } as unknown as AuthService;

    TestBed.configureTestingModule({
      imports: [ManagementReportsPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: auth },
      ],
    });

    const fixture = TestBed.createComponent(ManagementReportsPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, auth };
  }

  it('deshabilita la exportación sin reports.download', () => {
    const ctx = setup(false);
    expect(ctx.component.canExport()).toBe(false);
  });

  it('habilita la exportación con reports.download', () => {
    const ctx = setup(true);
    expect(ctx.component.canExport()).toBe(true);
  });

  it('consulta el permiso reports.download en hasPermission', () => {
    const ctx = setup(true);

    void ctx.component.canExport();
    expect(ctx.auth.hasPermission).toHaveBeenCalledWith('reports.download');
  });
});
