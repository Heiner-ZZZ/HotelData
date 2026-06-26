import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { SettingsApiService } from '../../settings/services/settings-api.service';
import type { SettingsViewModel } from '../../settings/models/settings.model';
import {
  DASHBOARD_OPTIONS,
  THEME_OPTIONS,
} from '../../settings/models/settings.model';
import { AuthService } from '../../../../core/auth/auth.service';
import { ThemeService } from '../../../../core/theme/theme.service';
import { toast } from '../../../../core/toast/toast.service';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';

@Component({
  selector: 'app-settings-page',
  imports: [ReactiveFormsModule, PageHeaderComponent],
  templateUrl: './settings-page.html',
  styleUrl: './settings-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly settingsApi = inject(SettingsApiService);
  private readonly authService = inject(AuthService);
  private readonly themeService = inject(ThemeService);

  readonly currentUser = this.authService.currentUser;

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');
  readonly settings = signal<SettingsViewModel | null>(null);
  readonly activeTab = signal<'security' | 'preferences'>('security');

  readonly tabs = [
    { key: 'security' as const, label: 'Seguridad', icon: 'lock' },
    { key: 'preferences' as const, label: 'Preferencias', icon: 'tune' },
  ];

  readonly dashboardOptions = DASHBOARD_OPTIONS;
  readonly themeOptions = THEME_OPTIONS;

  readonly form = this.formBuilder.nonNullable.group({
    defaultDashboard: ['/management'],
    theme: ['system'],
  });

  readonly passwordForm = this.formBuilder.nonNullable.group({
    currentPassword: ['', Validators.required],
    newPassword: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', Validators.required],
  });

  readonly changingPassword = signal(false);
  readonly passwordError = signal('');
  readonly passwordSuccess = signal('');

  constructor() {
    this.loadSettings();
  }

  private loadSettings(): void {
    this.loading.set(true);
    this.settingsApi
      .getSettings()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (s: SettingsViewModel) => {
          this.settings.set(s);
          this.form.patchValue({
            defaultDashboard: s.defaultDashboard,
            theme: s.theme,
          });
          this.applyTheme(s.theme);
          this.loading.set(false);
        },
        error: () => {
          this.errorMessage.set('No se pudieron cargar las configuraciones.');
          this.loading.set(false);
        },
      });
  }

  setTab(tab: 'security' | 'preferences'): void {
    this.activeTab.set(tab);
  }

  save(): void {
    if (this.form.invalid) return;

    this.saving.set(true);
    this.successMessage.set('');
    this.errorMessage.set('');

    const dashboard = this.form.controls.defaultDashboard.value;
    const theme = this.form.controls.theme.value;

    this.settingsApi
      .updateSettings({
        default_dashboard: dashboard,
        theme,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated: SettingsViewModel) => {
          this.settings.set(updated);
          localStorage.setItem('hoteldata-default-dashboard', updated.defaultDashboard);
          this.applyTheme(updated.theme);
          this.successMessage.set('Configuración guardada correctamente.');
          toast('Configuración guardada correctamente.', 'success', 3000);
          this.saving.set(false);
          setTimeout(() => this.successMessage.set(''), 3000);
        },
        error: (err: { message?: string }) => {
          this.errorMessage.set(err.message || 'No se pudieron guardar los cambios.');
          this.saving.set(false);
        },
      });
  }

  private applyTheme(theme: string): void {
    localStorage.setItem('hoteldata-theme-preference', theme);
    const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    localStorage.setItem('hoteldata-theme', isDark ? 'dark' : 'light');
  }

  changePassword(): void {
    if (this.passwordForm.invalid) {
      this.passwordForm.markAllAsTouched();
      return;
    }

    const { currentPassword, newPassword, confirmPassword } = this.passwordForm.getRawValue();
    if (newPassword !== confirmPassword) {
      this.passwordError.set('Las contraseñas no coinciden.');
      return;
    }

    this.changingPassword.set(true);
    this.passwordError.set('');
    this.passwordSuccess.set('');

    this.settingsApi
      .changePassword(currentPassword, newPassword)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.passwordSuccess.set('Contraseña actualizada correctamente.');
          this.passwordForm.reset();
          this.changingPassword.set(false);
          setTimeout(() => this.passwordSuccess.set(''), 3000);
        },
        error: (err: { message?: string }) => {
          this.passwordError.set(err.message || 'Error al cambiar la contraseña.');
          this.changingPassword.set(false);
        },
      });
  }
}
