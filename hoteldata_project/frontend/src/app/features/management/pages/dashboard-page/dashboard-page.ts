import { ChangeDetectionStrategy, Component } from '@angular/core';

import { DashboardPageComponent } from '../../../admin/pages/dashboard-page/dashboard-page';

@Component({
  selector: 'app-management-dashboard-page',
  imports: [DashboardPageComponent],
  template: '<app-dashboard-page />',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManagementDashboardPageComponent {}
