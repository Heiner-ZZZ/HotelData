import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { httpResource } from '@angular/common/http';

import { SettingsApiService } from '../../settings/services/settings-api.service';
import type { SettingsViewModel } from '../../settings/models/settings.model';
import {
  DASHBOARD_OPTIONS,
  THEME_OPTIONS,
  type SelectOption,
} from '../../settings/models/settings.model';
import { AuthService } from '../../../../core/auth/auth.service';
import { ThemeService } from '../../../../core/theme/theme.service';
import { OperationModeService, type OperationMode } from '../../../../core/services/operation-mode.service';
import { ModeHighlightDirective } from '../../../../core/directives/mode-highlight.directive';
import { ToastService } from '../../../../shared/services/toast.service';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';

interface NavItem {
  label: string;
  href: string;
  icon: string;
  visible: boolean;
}

@Component({
  selector: 'app-settings-page',
  imports: [ReactiveFormsModule, PageHeaderComponent, ModeHighlightDirective],
  templateUrl: './settings-page.html',
  styleUrl: './settings-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly settingsApi = inject(SettingsApiService);
  private readonly authService = inject(AuthService);
  private readonly theme = inject(ThemeService);
  private readonly toast = inject(ToastService);
  private readonly opMode = inject(OperationModeService);
  private readonly router = inject(Router);

  readonly currentUser = this.authService.currentUser;

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly settings = signal<SettingsViewModel | null>(null);
  readonly activeTab = signal<'security' | 'preferences'>('security');

  readonly tabs = [
    { key: 'security' as const, label: 'Seguridad', icon: 'lock' },
    { key: 'preferences' as const, label: 'Preferencias', icon: 'tune' },
  ];

  readonly themeOptions = THEME_OPTIONS;

  /** Navigation items from backend, filtered by user permissions. */
  private readonly navResource = httpResource<{ items: NavItem[] }>(() => '/api/admin/navigation', {
    defaultValue: { items: [] },
  });

  /** User-accessible hrefs from the navigation API. */
  private readonly accessibleHrefs = computed(() => {
    const items = this.navResource.value()?.items ?? [];
    return new Set(items.filter(i => i.visible).map(i => i.href));
  });

  /** Dashboard options filtered to only routes the user can access.
   *  Falls back to the hardcoded list if the navigation API hasn't loaded yet. */
  readonly dashboardOptions = computed<SelectOption[]>(() => {
    // Still loading navigation — show all options temporarily
    if (this.navResource.isLoading()) return DASHBOARD_OPTIONS;
    const allowed = this.accessibleHrefs();
    if (allowed.size === 0) return DASHBOARD_OPTIONS;
    const filtered = DASHBOARD_OPTIONS.filter(opt => allowed.has(opt.value));
    // Always ensure at least one option is available
    return filtered.length > 0 ? filtered : DASHBOARD_OPTIONS;
  });

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

  /** Snapshot reactivo del form de preferencias (patrón de promotion-form/profile). */
  private readonly prefsFormValues = toSignal(this.form.valueChanges, {
    initialValue: this.form.getRawValue(),
  });

  /** Snapshot reactivo del form de contraseña. */
  private readonly passwordFormValues = toSignal(this.passwordForm.valueChanges, {
    initialValue: this.passwordForm.getRawValue(),
  });

  /**
   * ¿Hay cambios sin guardar en preferencias? Compara por valor contra lo
   * cargado (editar y revertir no cuenta).
   */
  readonly hasUnsavedChanges = computed<boolean>(() => {
    const s = this.settings();
    const v = this.prefsFormValues();
    if (!s || !v) return false;
    return v.defaultDashboard !== s.defaultDashboard || v.theme !== s.theme;
  });

  /** ¿El usuario está escribiendo una contraseña nueva? (algún campo con contenido). */
  readonly passwordEntry = computed<boolean>(() => {
    const v = this.passwordFormValues();
    return !!(v.currentPassword || v.newPassword || v.confirmPassword);
  });

  /**
   * Modo CRUD de la página de settings: cada pestaña es un form independiente
   * y solo la pestaña activa manda en el nav (patrón de secciones de rates).
   */
  private readonly _opMode = computed<{ mode: OperationMode; detail: string }>(() => {
    if (this.activeTab() === 'security') {
      return this.passwordEntry()
        ? { mode: 'update', detail: 'Contraseña' }
        : { mode: 'read', detail: '' };
    }
    return this.hasUnsavedChanges()
      ? { mode: 'update', detail: 'Preferencias' }
      : { mode: 'read', detail: '' };
  });

  constructor() {
    this.loadSettings();

    // Modo CRUD reactivo en el nav: Solo lectura ↔ Editando según el estado de
    // la pestaña activa (contraseña en curso / preferencias con cambios).
    effect(() => {
      const m = this._opMode();
      this.opMode.setMode(m.mode, m.detail);
    });
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
          // La BD ya es la fuente de verdad (se leyó de /api/settings); solo
          // aplicamos sin volver a persistir.
          this.theme.setPreference(s.theme as 'system' | 'light' | 'dark', false);
          this.loading.set(false);
        },
        error: () => {
          this.toast.error('No se pudieron cargar las configuraciones.');
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
          // Misma fuente de verdad que el icono del nav: ya se persistió en el
          // PUT de arriba, solo se aplica (persist=false evita el doble PUT).
          this.theme.setPreference(updated.theme as 'system' | 'light' | 'dark', false);
          this.toast.success('Configuración guardada correctamente.');
          this.saving.set(false);
        },
        error: (err: { message?: string }) => {
          this.toast.error(err.message || 'No se pudieron guardar los cambios.');
          this.saving.set(false);
        },
      });
  }

  changePassword(): void {
    if (this.passwordForm.invalid) {
      this.passwordForm.markAllAsTouched();
      return;
    }

    const { currentPassword, newPassword, confirmPassword } = this.passwordForm.getRawValue();
    if (newPassword !== confirmPassword) {
      this.toast.error('Las contraseñas no coinciden.');
      return;
    }

    this.changingPassword.set(true);

    this.settingsApi
      .changePassword(currentPassword, newPassword)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.toast.success('Contraseña actualizada. Inicia sesión nuevamente.');
          this.passwordForm.reset();
          this.changingPassword.set(false);
          this.authService.invalidateSession();
          setTimeout(() => void this.router.navigate(['/login']), 1500);
        },
        error: (err: { message?: string }) => {
          this.toast.error(err.message || 'Error al cambiar la contraseña.');
          this.changingPassword.set(false);
        },
      });
  }
}
