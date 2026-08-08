import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  OnInit,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { HotelRole, RoleAssignment, TeamMember } from '../../models/hotel-permissions.model';
import { HotelPermissionsApiService } from '../../services/hotel-permissions-api.service';

@Component({
  selector: 'app-assign-role-modal',
  imports: [ReactiveFormsModule],
  templateUrl: './assign-role-modal.html',
  styleUrl: './assign-role-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AssignRoleModalComponent implements OnInit {
  private readonly propCtx = inject(PropertyContextService);
  private readonly api = inject(HotelPermissionsApiService);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  /** Roles activos del hotel (opciones). */
  readonly roles = input<HotelRole[]>([]);
  /** Asignación a cambiar (modo "cambiar rol"); null = asignar a un miembro sin rol. */
  readonly assignment = input<RoleAssignment | null>(null);
  /** Miembro sin rol a asignar (modo "asignar"). */
  readonly member = input<TeamMember | null>(null);
  readonly close = output<void>();
  readonly saved = output<void>();

  readonly form = this.fb.nonNullable.group({
    role_id: ['', [Validators.required]],
  });

  readonly saving = signal(false);
  readonly submitError = signal<string | null>(null);

  readonly isChanging = computed(() => !!this.assignment());
  readonly activeRoles = computed(() => this.roles().filter((r) => r.isActive));
  readonly currentRoleId = computed(() => this.assignment()?.roleId ?? '');

  readonly userLabel = computed(() => {
    const assignment = this.assignment();
    const member = this.member();
    return assignment
      ? assignment.displayName || assignment.username
      : (member?.displayName || member?.username || '');
  });

  readonly userHandle = computed(() => {
    const assignment = this.assignment();
    const member = this.member();
    return assignment ? assignment.username : (member?.username ?? '');
  });

  /** Opciones: roles activos + (si el rol actual quedó inactivo) el rol actual. */
  readonly roleOptions = computed<HotelRole[]>(() => {
    const currentId = this.currentRoleId();
    const current = this.roles().find((r) => r.id === currentId);
    if (current && !current.isActive) {
      return [...this.activeRoles(), current];
    }
    return this.activeRoles();
  });

  ngOnInit(): void {
    const roleId = this.currentRoleId();
    if (roleId) {
      this.form.patchValue({ role_id: roleId });
    }
  }

  submit(): void {
    if (this.saving()) return;
    this.form.get('role_id')?.markAsTouched();
    if (this.form.controls.role_id.invalid) {
      this.submitError.set('Selecciona un rol.');
      return;
    }

    const propId = this.propCtx.currentPropId();
    if (!propId) {
      this.submitError.set('No hay propiedad seleccionada.');
      return;
    }

    const roleId = this.form.controls.role_id.value;
    const assignment = this.assignment();
    const member = this.member();
    if (!assignment && !member) {
      this.submitError.set('Falta el miembro del equipo.');
      return;
    }

    this.saving.set(true);
    this.submitError.set(null);

    const request = assignment
      ? this.api.changeAssignmentRole(propId, assignment.id, { role_id: roleId })
      : this.api.assignUser(propId, { user_id: member!.userId, role_id: roleId });

    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.saving.set(false);
        this.saved.emit();
      },
      error: (err: unknown) => {
        this.saving.set(false);
        this.submitError.set(this.errorMessage(err));
      },
    });
  }

  private errorMessage(err: unknown): string {
    const httpErr = err as HttpErrorResponse;
    const detail = httpErr?.error?.detail;
    return typeof detail === 'string' && detail ? detail : 'Error al guardar la asignación.';
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget && !this.saving()) {
      this.close.emit();
    }
  }

  cancel(): void {
    if (!this.saving()) this.close.emit();
  }
}
