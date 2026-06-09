import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import type { CheckInRowViewModel } from '../../models/check-ins.model';

@Component({
  selector: 'app-check-ins-table',
  templateUrl: './check-ins-table.html',
  styleUrl: './check-ins-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckInsTableComponent {
  readonly items = input.required<CheckInRowViewModel[]>();
  readonly complete = output<string>();
}
