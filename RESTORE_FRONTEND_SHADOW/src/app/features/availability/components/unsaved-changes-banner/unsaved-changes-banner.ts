import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-unsaved-changes-banner',
  standalone: true,
  templateUrl: './unsaved-changes-banner.html',
  styleUrl: './unsaved-changes-banner.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UnsavedChangesBannerComponent {
  readonly count = input(0);
  readonly hasErrors = input(false);
  readonly saving = input(false);

  readonly save = output<void>();
  readonly discard = output<void>();
}
