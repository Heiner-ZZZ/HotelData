import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ToastService } from '../../../../../shared/services/toast.service';
import { ProfileApiService } from '../../../services/profile-api.service';

@Component({
  selector: 'app-profile-security',
  templateUrl: './profile-security.html',
  styleUrl: './profile-security.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProfileSecurityComponent {
  private readonly profileApi = inject(ProfileApiService);
  private readonly toast = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);

  // ═══ Data loading — httpResource (replaces manual GET + subscribe) ═══
  readonly sessionsResource = httpResource<{ items: unknown[]; total: number }>(() => '/auth/sessions');

  readonly totalSessions = signal(0);
  readonly loadingSessions = signal(false);
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
  }

  cancelTerminate(): void {
    this.confirmingTerminate.set(false);
  }

  terminateOtherSessions(): void {
    this.terminating.set(true);

    this.profileApi.terminateOtherSessions()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.terminating.set(false);
          this.confirmingTerminate.set(false);
          this.toast.success(response.message);
          this.totalSessions.update((v) => Math.max(1, v - response.terminated_count));
        },
        error: (error) => {
          this.terminating.set(false);
          this.toast.error(error?.error?.detail || 'Error al cerrar sesiones.');
        },
      });
  }
}
