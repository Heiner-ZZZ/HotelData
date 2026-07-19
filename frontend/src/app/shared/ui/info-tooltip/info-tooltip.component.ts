import {
  ChangeDetectionStrategy,
  Component,
  input
} from '@angular/core';

/**
 * Global info-tooltip component. Renders a small (i) icon that shows a styled
 * popover on hover (desktop). Hover-only — no click toggle, no pinning.
 *
 * @example
 * <app-info-tooltip text="Check-in y check-out son globales para todo el hotel."></app-info-tooltip>
 * <app-info-tooltip title="Rango de estancia" text="Define el rango de noches permitido." icon="nights_stay"></app-info-tooltip>
 */
@Component({
  selector: 'app-info-tooltip',
  standalone: true,
  templateUrl: './info-tooltip.component.html',
  styleUrls: ['./info-tooltip.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class InfoTooltipComponent {
  /** Tooltip body text. Supports <strong>, <em>, <ul><li> HTML. */
  readonly text = input.required<string>();

  /** Optional title shown in the popover header row. */
  readonly title = input<string>();

  /** Optional material icon name (defaults to 'info'). */
  readonly icon = input<string>('info');
}
