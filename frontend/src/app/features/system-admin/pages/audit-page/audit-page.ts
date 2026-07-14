import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { AuditViewModel } from '../../models/audit.model';
import type { AuditActivityDto } from '../../models/audit.dto';
import { mapAuditActivity } from '../../mappers/audit.mapper';

@Component({
  selector: 'app-audit-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './audit-page.html',
  styleUrl: './audit-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuditPageComponent {
  readonly activityResource = httpResource<AuditViewModel>(() => '/api/audit/activity', {
    parse: (dto) => mapAuditActivity(dto as AuditActivityDto),
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.activityResource.isLoading()) return 'loading';
    if (this.activityResource.error()) return 'error';
    const vm = this.activityResource.value();
    if (!vm) return 'loading';
    return vm.totalExecutions > 0 || vm.totalSearches > 0 ? 'success' : 'empty';
  });

  readonly loadErrorMessage = computed(() => {
    const err = this.activityResource.error();
    return (err as unknown as ApiError)?.message || '';
  });

  readonly openSection = signal<string | null>(null);

  toggleSection(key: string) {
    this.openSection.update(v => v === key ? null : key);
  }
}
