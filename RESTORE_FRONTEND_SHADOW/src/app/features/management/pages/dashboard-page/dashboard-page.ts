import { ChangeDetectionStrategy, Component } from '@angular/core';

import { DashboardPageComponent as LegacyDashboardPageComponent } from '../../../admin/pages/dashboard-page/dashboard-page';

@Component({
  selector: 'app-management-dashboard-page',
  standalone: true,
  imports: [LegacyDashboardPageComponent],
  template: '<app-dashboard-page />',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManagementDashboardPageComponent {}
