import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ProfileApiService } from '../../../services/profile-api.service';

@Component({
  selector: 'app-profile-security',
  templateUrl: './profile-security.html',
  styleUrl: './profile-security.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProfileSecurityComponent {
  private readonly profileApi = inject(ProfileApiService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly Math = Math;

  // ═══ Data loading — httpResource (replaces manual GET + subscribe) ═══
  readonly sessionsResource = httpResource<{ items: unknown[]; total: number }>(() => '/auth/sessions');

  readonly totalSessions = signal(0);
  readonly loadingSessions = signal(false);
  readonly sessionsMessage = signal('');
  readonly sessionsError = signal('');
  readonly confirmingTerminate = signal(false);
  readonly terminating = signal(false);

  constructor() {
    effect(() => {
      const res = this.sessionsResource.value();
      if (res) {
        this.totalSessions.set(res.total);
      }
    });

    effect(() => {
      this.loadingSessions.set(this.sessionsResource.isLoading());
    });
  }

  requestTerminate(): void {
    this.confirmingTerminate.set(true);
    this.sessionsMessage.set('');
    this.sessionsError.set('');
  }

  cancelTerminate(): void {
    this.confirmingTerminate.set(false);
  }

  terminateOtherSessions(): void {
    this.terminating.set(true);
    this.sessionsMessage.set('');
    this.sessionsError.set('');

    this.profileApi.terminateOtherSessions()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.terminating.set(false);
          this.confirmingTerminate.set(false);
          this.sessionsMessage.set(response.message);
          this.totalSessions.update((v) => Math.max(1, v - response.terminated_count));
          setTimeout(() => this.sessionsMessage.set(''), 4000);
        },
        error: (error) => {
          this.terminating.set(false);
          this.sessionsError.set(error?.error?.detail || 'Error al cerrar sesiones.');
          setTimeout(() => this.sessionsError.set(''), 4000);
        },
      });
  }
}
