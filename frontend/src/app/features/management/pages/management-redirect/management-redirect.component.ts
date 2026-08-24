import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { pickFirstAccessibleManagementHref } from '../../management-redirect';

@Component({
  selector: 'app-management-redirect',
  standalone: true,
  template: `<p style="padding:2rem;text-align:center">Redirigiendo…</p>`,
})
export class ManagementRedirectComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  ngOnInit(): void {
    const state = this.auth.authState();
    if (!state.authenticated) {
      void this.router.navigateByUrl('/login');
      return;
    }

    const href = pickFirstAccessibleManagementHref(
      state.permissionCodes,
      state.user?.primaryRole ?? null,
    );

    const queryParams = this.route.snapshot.queryParams;
    void this.router.navigateByUrl(
      this.router.createUrlTree([href], { queryParams }).toString(),
    );
  }
}
