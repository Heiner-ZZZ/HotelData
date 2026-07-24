import { DatePipe, NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-pp-hero',
  standalone: true,
  imports: [DatePipe, NgOptimizedImage],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="profile-hero">
      <div class="avatar-ring" (click)="onAvatarClick()" [class.avatar-ring--clickable]="vm()?.avatarUrl">
        @if (vm()?.avatarUrl; as url) {
          <img [ngSrc]="url" width="72" height="72" alt="Avatar" class="avatar-img" />
        } @else {
          <span class="material-symbols-outlined avatar-icon">person</span>
        }
      </div>
      <div class="hero-text">
        <h1>{{ vm()?.displayName }}</h1>
        <p class="hero-username">&#64;{{ vm()?.username }}</p>
        <div class="hero-badges">
          <span class="badge badge-role">{{ vm()?.primaryRoleLabel }}</span>
          <span class="badge" [class.badge-active]="vm()?.isActive" [class.badge-inactive]="!vm()?.isActive">
            {{ vm()?.isActive ? 'Activo' : 'Inactivo' }}
          </span>
          <span class="badge badge-muted">
            Miembro desde {{ vm()?.createdAt | date:'MMM y' }}
          </span>
        </div>
      </div>
    </header>
  `
})
export class PpHeroComponent {
  readonly vm = input<any>(null);
  readonly avatarClick = output<void>();

  protected onAvatarClick(): void {
    if (this.vm()?.avatarUrl) {
      this.avatarClick.emit();
    }
  }
}
