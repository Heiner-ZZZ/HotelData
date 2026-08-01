import { ChangeDetectionStrategy, Component, computed, inject, ViewEncapsulation } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ApiError } from '../../../../core/api/api-error.model';
import { SystemPermissionsContextService } from '../../services/system-permissions-context.service';

@Component({
  selector: 'app-system-permissions-page',
  standalone: true,
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './system-permissions-page.html',
  styleUrl: './system-permissions-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class SystemPermissionsPageComponent {
  readonly context = inject(SystemPermissionsContextService);
  readonly loadErrorMessage = computed(() => (this.context.overviewResource.error() as unknown as ApiError)?.message || '');
}
