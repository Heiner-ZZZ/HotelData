import { httpResource } from '@angular/common/http';

import { getErrorMessage } from '../../../../shared/utils/http-error.util';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { fromEvent, interval } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { toast } from '../../../../core/toast/toast.service';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { RegistrationStatusDto } from '../../models/registration-status.dto';
import {
  PROPERTY_TYPES,
  propertyTypeLabel,
  type RegistrationStatus,
} from '../../models/registration-status.model';
import {
  mapRegistrationStatus,
  RegistrationStatusApiService,
} from '../../services/registration-status-api.service';

/** E.164 phone regex (misma regla que el wizard de onboarding). */
const PHONE_PATTERN = /^\+?[1-9]\d{6,14}$/;

/** Polling del estado del registro: 60 s (spec UX-3 §3.5). */
const POLL_INTERVAL_MS = 60_000;

const STATUS_ICONS: Record<string, string> = {
  submitted: 'mark_email_read',
  edited: 'edit',
  resubmitted: 'refresh',
  changes_requested: 'feedback',
  rejected: 'close',
  approved: 'check_circle',
};

const STATUS_LABELS: Record<string, string> = {
  submitted: 'Registro recibido',
  edited: 'Datos actualizados',
  resubmitted: 'Registro reenviado',
  changes_requested: 'Cambios solicitados',
  rejected: 'Rechazado',
  approved: 'Aprobado',
};

@Component({
  selector: 'app-registration-status-page',
  imports: [ReactiveFormsModule, RouterLink, LoadingStateComponent, ErrorStateComponent],
  templateUrl: './registration-status-page.html',
  styleUrl: './registration-status-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegistrationStatusPageComponent {
  private readonly api = inject(RegistrationStatusApiService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly propertyTypes = PROPERTY_TYPES;

  // ── Estado del registro: GET con polling 60 s ──────────────────────
  // httpResource se recarga solo cada 60 s y cada vez que el usuario vuelve
  // a la pestaña (focus / visibilitychange) — spec UX-3 §3.5.
  readonly statusResource = httpResource<RegistrationStatus>(
    () => ({ url: '/api/auth/registration-status' }),
    {
      parse: (dto) => mapRegistrationStatus(dto as RegistrationStatusDto),
    },
  );

  /** Valor seguro: `value()` re-lanza el error del recurso cuando hay uno
   *  (404/401), así que se guarda contra `error()` para que el template y el
   *  efecto de transición no exploten con recursos en estado de error. */
  readonly status = computed<RegistrationStatus | null>(() => {
    if (this.statusResource.error()) return null;
    return this.statusResource.value() ?? null;
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.statusResource.isLoading()) return 'loading';
    if (this.statusResource.error()) return 'error';
    return this.statusResource.value() ? 'success' : 'loading';
  });

  // ── Detección de transiciones (approved → dashboard, rejected → toast) ──
  private readonly previousStatus = signal<string | null>(null);

  readonly transitionEffect = effect(() => {
    const current = this.status()?.approvalStatus ?? null;
    const previous = this.previousStatus();
    this.previousStatus.set(current);
    if (current === null || current === previous) return;
    if (current === 'approved') {
      toast('¡Tu alojamiento fue aprobado!', 'success');
      void this.router.navigateByUrl(this.auth.authState().homeHref || '/search');
    } else if (current === 'rejected') {
      toast('Tu registro no fue aprobado. Revisa el motivo.', 'warning');
    }
  });

  constructor() {
    // Polling 60 s (spec UX-3 §3.5): esta versión de httpResource no expone
    // pollingInterval, así que recargamos con un interval + reload() declarativo.
    interval(POLL_INTERVAL_MS)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.statusResource.reload());
    // Re-check al volver a la pestaña (además del polling).
    fromEvent(window, 'focus')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.statusResource.reload());
    fromEvent(document, 'visibilitychange')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (!document.hidden) this.statusResource.reload();
      });
  }

  // ── Derivados de estado ────────────────────────────────────────────
  readonly isPending = computed(() => this.status()?.approvalStatus === 'pending_approval');
  readonly isChangesRequested = computed(() => this.status()?.approvalStatus === 'changes_requested');
  readonly isRejected = computed(() => this.status()?.approvalStatus === 'rejected');
  readonly isEditable = computed(() => this.isPending() || this.isChangesRequested());

  // ── Descuento por pago anual (UX-3: transparencia de precios) ──────
  /** USD ahorrados al año pagando el plan por adelantado: (mensual − anual) × 12. */
  readonly bandAnnualSavings = computed<number>(() => {
    const band = this.status()?.suggestedBand;
    if (!band || band.annualMonthlyUsd == null) return 0;
    return Math.max(0, Math.round((band.monthlyUsd - band.annualMonthlyUsd) * 12));
  });

  /** % de descuento del plan anual (≈22–27%) — solo para el badge. */
  readonly bandAnnualDiscountPct = computed<number>(() => {
    const band = this.status()?.suggestedBand;
    if (!band || band.annualMonthlyUsd == null || band.monthlyUsd <= 0) return 0;
    return Math.round((1 - band.annualMonthlyUsd / band.monthlyUsd) * 100);
  });

  propertyTypeLabel = propertyTypeLabel;

  /** Label humano de un evento del timeline (fallback al detail del backend). */
  timelineLabel(event: string, detail: string): string {
    return STATUS_LABELS[event] ?? (detail || event);
  }

  timelineIcon(event: string): string {
    return STATUS_ICONS[event] ?? 'schedule';
  }

  /** Fecha ISO → formato local (es). */
  formatDate(iso: string | null): string {
    if (!iso) return '';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat('es', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  }

  // ── Formulario de edición (PATCH /api/auth/register-property/me) ───
  readonly editOpen = signal(false);
  readonly editSaving = signal(false);
  readonly editError = signal('');

  readonly editForm = this.formBuilder.nonNullable.group({
    property_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(120)]],
    property_type: ['', [Validators.required]],
    contact_phone: ['', [Validators.required, Validators.pattern(PHONE_PATTERN)]],
    city: ['', [Validators.required, Validators.minLength(2)]],
    total_rooms: [1, [Validators.required, Validators.min(1), Validators.max(10000)]],
    description: ['', [Validators.maxLength(500)]],
  });

  openEdit(): void {
    const property = this.status()?.property;
    if (property) {
      this.editForm.patchValue({
        property_name: property.name,
        property_type: property.type,
        contact_phone: property.contactPhone,
        city: property.city,
        total_rooms: property.totalRooms,
        description: '',
      });
    }
    this.editError.set('');
    this.editOpen.set(true);
  }

  closeEdit(): void {
    this.editOpen.set(false);
  }

  submitEdit(): void {
    if (this.editForm.invalid || this.editSaving()) {
      this.editForm.markAllAsTouched();
      return;
    }
    const raw = this.editForm.getRawValue();
    this.editSaving.set(true);
    this.editError.set('');
    this.api
      .editProperty({
        property_name: raw.property_name,
        property_type: raw.property_type,
        contact_phone: raw.contact_phone,
        city: raw.city,
        total_rooms: raw.total_rooms,
        description: raw.description,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.editSaving.set(false);
          toast(response.message || 'Datos actualizados.', 'success');
          this.editOpen.set(false);
          // Refresca datos + timeline + banda sugerida (recalculada si cambió
          // total_rooms); el polling sigue activo.
          this.statusResource.reload();
        },
        error: (err: unknown) => {
          this.editSaving.set(false);
          this.editError.set(getErrorMessage(err) || 'No se pudieron guardar los cambios.');
        },
      });
  }

  // ── Estado rechazado ───────────────────────────────────────────────
  /** Cerrar sesión: invalida server-side vía /auth/logout (web, permitido por
   *  la allowlist) y limpia el estado local. Funciona en dev (proxy /auth) y
   *  prod (nginx /auth/). */
  logout(): void {
    void fetch('/auth/logout', { credentials: 'include' })
      .catch(() => undefined)
      .finally(() => {
        this.auth.invalidateSession();
        void this.router.navigateByUrl('/login');
      });
  }
}
