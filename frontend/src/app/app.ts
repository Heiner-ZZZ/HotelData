import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ToastContainerComponent } from './shared/ui/toast/toast';
import { VersionBannerComponent } from './shared/ui/version-banner/version-banner';
import { ConfirmDialogComponent } from './shared/ui/confirm-dialog/confirm-dialog.component';
import { VersionCheckService } from './core/services/version-check.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, ToastContainerComponent, VersionBannerComponent, ConfirmDialogComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  constructor() {
    inject(VersionCheckService).startPolling();
  }
}
