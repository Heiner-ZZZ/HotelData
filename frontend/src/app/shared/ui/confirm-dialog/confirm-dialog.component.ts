import { ChangeDetectionStrategy, Component, HostListener, inject } from '@angular/core';

import { ConfirmDialogService } from './confirm-dialog.service';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  styleUrl: './confirm-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (service.isOpen()) {
      <div class="cd-backdrop" (click)="service.cancel()">
        <div class="cd-dialog" role="dialog" aria-modal="true" aria-labelledby="cd-title" (click)="$event.stopPropagation()">
          <div class="cd-header">
            <span class="cd-icon"
                  [class.cd-icon-danger]="service.config().variant === 'danger'"
                  [class.cd-icon-warning]="service.config().variant === 'warning'">
              <span class="material-symbols-outlined">
                {{ service.config().variant === 'danger' ? 'warning' : 'help' }}
              </span>
            </span>
            <h3 id="cd-title" class="cd-title">{{ service.config().title }}</h3>
          </div>

          <p class="cd-message">{{ service.config().message }}</p>

          <div class="cd-actions">
            <button class="cd-btn cd-btn-cancel" (click)="service.cancel()">
              {{ service.config().cancelLabel }}
            </button>
            <button class="cd-btn cd-btn-confirm"
                    [class.cd-btn-danger]="service.config().variant === 'danger'"
                    [class.cd-btn-warning]="service.config().variant === 'warning'"
                    (click)="service.confirm()">
              {{ service.config().confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class ConfirmDialogComponent {
  readonly service = inject(ConfirmDialogService);

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.service.isOpen()) this.service.cancel();
  }
}
