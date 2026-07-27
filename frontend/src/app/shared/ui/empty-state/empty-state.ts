import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  templateUrl: './empty-state.html',
  styleUrl: './empty-state.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EmptyStateComponent {
  readonly title = input.required<string>();
  /**
   * @deprecated Use `description` instead. Kept as alias for backward compat
   * with cogs-report / margin-report / products-list-page templates that
   * already pass `message="..."`. Falls back to `description` when not set.
   */
  readonly message = input('');
  readonly description = input('');
  readonly icon = input('');
}