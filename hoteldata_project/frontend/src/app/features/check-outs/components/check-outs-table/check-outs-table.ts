import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import type { CheckOutRowViewModel } from '../../models/check-outs.model';

@Component({
  selector: 'app-check-outs-table',
  templateUrl: './check-outs-table.html',
  styleUrl: './check-outs-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckOutsTableComponent {
  readonly items = input.required<CheckOutRowViewModel[]>();
  readonly complete = output<string>();
}
