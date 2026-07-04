import { Component, inject } from '@angular/core';
import { VersionCheckService } from '../../../core/services/version-check.service';

@Component({
  selector: 'app-version-banner',
  standalone: true,
  templateUrl: './version-banner.html',
  styleUrl: './version-banner.scss',
})
export class VersionBannerComponent {
  readonly versionCheck = inject(VersionCheckService);

  reload(): void {
    this.versionCheck.applyUpdate();
  }

  dismiss(): void {
    this.versionCheck.dismiss();
  }
}
