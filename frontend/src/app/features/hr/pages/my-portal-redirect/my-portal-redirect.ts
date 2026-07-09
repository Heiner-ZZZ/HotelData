import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { HrApiService } from '../../services/hr-api.service';

@Component({
  selector: 'app-my-portal-redirect',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="display: flex; align-items: center; justify-content: center; padding: 4rem; gap: 0.75rem; color: var(--muted-text);">
      <span class="material-symbols-outlined spin">progress_activity</span>
      <span>Redirigiendo a tu portal...</span>
    </div>
  `,
})
export class MyPortalRedirectComponent {
  private readonly hrApi = inject(HrApiService);
  private readonly router = inject(Router);

  constructor() {
    this.hrApi.getMyPortal().subscribe({
      next: (res) => this.router.navigateByUrl(res.portal_url),
      error: () => this.router.navigateByUrl('/management/hr/directory'),
    });
  }
}
