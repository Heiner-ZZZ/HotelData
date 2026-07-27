import { Component, input } from '@angular/core';

@Component({
  selector: 'app-page-header',
  templateUrl: './page-header.html',
  styleUrl: './page-header.scss'
})
export class PageHeaderComponent {
  readonly eyebrow = input('');
  readonly title = input.required<string>();
  /**
   * @deprecated Use `description` instead. Kept as alias for backward compat
   * with the 4 product-feature templates (cogs-report, margin-report,
   * products-list-page, products-form-page) that already pass `[subtitle]`.
   * Falls back to `description` when not set.
   */
  readonly subtitle = input('');
  readonly description = input('');
  /**
   * Optional Material Symbols icon name rendered before the title block.
   * Several product templates already pass `icon="inventory_2"` etc.; without
   * this input Angular strict-template check raised NG8002. Kept for
   * backward compatibility. Render the icon in the template; design it
   * properly when the design system lands an icon treatment for headers.
   */
  readonly icon = input('');
}
