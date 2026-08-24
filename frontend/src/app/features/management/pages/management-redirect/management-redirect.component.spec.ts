import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { ManagementRedirectComponent } from './management-redirect.component';

describe('ManagementRedirectComponent — redirección dinámica de /management (TDD)', () => {
  function setup(opts: {
    permissionCodes: string[];
    role: string | null;
    queryParams?: Record<string, string>;
    authenticated?: boolean;
  }) {
    const navigateByUrl = jest.fn();
    const createUrlTree = jest.fn((commands: string[], extras?: { queryParams: Record<string, string> }) => {
      const qp = extras?.queryParams ? `?${new URLSearchParams(extras.queryParams).toString()}` : '';
      return { toString: () => `${commands[0]}${qp}` } as unknown as ReturnType<Router['createUrlTree']>;
    });

    TestBed.configureTestingModule({
      imports: [ManagementRedirectComponent],
      providers: [
        {
          provide: AuthService,
          useValue: {
            authState: () => ({
              authenticated: opts.authenticated ?? true,
              user: opts.role ? { primaryRole: opts.role } as unknown as ReturnType<AuthService['currentUser']> : null,
              permissionCodes: opts.permissionCodes,
              homeHref: null,
              session: null,
            }),
          },
        },
        {
          provide: Router,
          useValue: { navigateByUrl, createUrlTree } as unknown as Router,
        },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParams: opts.queryParams ?? {} } } as unknown as ActivatedRoute,
        },
      ],
    });

    const fixture = TestBed.createComponent(ManagementRedirectComponent);
    fixture.detectChanges();
    return { navigateByUrl, createUrlTree };
  }

  it('housekeeping sin strategic → redirige a /management/housekeeping (no a h01)', () => {
    const { navigateByUrl } = setup({
      permissionCodes: ['housekeeping.read', 'dashboard.read'],
      role: 'housekeeping',
      queryParams: { prop_id: '1' },
    });
    expect(navigateByUrl).toHaveBeenCalled();
    const url = (navigateByUrl.mock.calls[0][0] as string) ?? '';
    expect(url).not.toContain('informes-estrategicos');
    expect(url).toContain('/management/housekeeping');
    expect(url).toContain('prop_id=1');
  });

  it('gerente con strategic → redirige a h01 preservando prop_id', () => {
    const { navigateByUrl } = setup({
      permissionCodes: ['reports.strategic.read', 'dashboard.read'],
      role: 'gerente_hotel',
      queryParams: { prop_id: '1', prop_label: 'Hotel Lima' },
    });
    const url = navigateByUrl.mock.calls[0][0] as string;
    expect(url).toContain('/management/informes-estrategicos/h01');
    expect(url).toContain('prop_id=1');
  });

  it('no autenticado → va a /login', () => {
    const { navigateByUrl } = setup({
      permissionCodes: [],
      role: null,
      authenticated: false,
    });
    expect(navigateByUrl).toHaveBeenCalledWith('/login');
  });
});
