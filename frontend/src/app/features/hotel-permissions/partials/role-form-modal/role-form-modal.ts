import { getErrorMessage } from '../../../../shared/utils/http-error.util';
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
import type { HotelRole, PermissionGroup, RoleTemplate } from '../../models/hotel-permissions.model';
import { HotelPermissionsApiService } from '../../services/hotel-permissions-api.service';

const HOTEL_MANAGE_ROLES = 'hotel.manage_roles';

@Component({
  selector: 'app-role-form-modal',
  imports: [ReactiveFormsModule],
  templateUrl: './role-form-modal.html',
  styleUrl: './role-form-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoleFormModalComponent implements OnInit {
  private readonly propCtx = inject(PropertyContextService);
  private readonly api = inject(HotelPermissionsApiService);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  /** Plantillas clonables (is_template / is_system fuera de NON_HOTEL_TEMPLATES). */
  readonly templates = input<RoleTemplate[]>([]);
  /** Catálogo de permisos agrupado por módulo (checkboxes). */
  readonly permissionGroups = input<PermissionGroup[]>([]);
  /** Rol en edición; null = crear/clonar. */
  readonly editing = input<HotelRole | null>(null);
  readonly close = output<void>();
  readonly saved = output<void>();

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    display_name: [''],
    based_on_role_id: [''],
  });

  readonly selectedPermissions = signal<Set<string>>(new Set());
  readonly saving = signal(false);
  readonly submitError = signal<string | null>(null);

  readonly isEditing = computed(() => !!this.editing());
  readonly grantedManageBefore = computed(
    () => this.editing()?.permissions.includes(HOTEL_MANAGE_ROLES) ?? false,
  );
  /** Advertencia: el rol pierde la administración del hotel (puede disparar 409 anti-lockout). */
  readonly manageRemovedWarning = computed(
    () => this.grantedManageBefore() && !this.selectedPermissions().has(HOTEL_MANAGE_ROLES),
  );
  /** Quirk del backend: crear con plantilla y 0 permisos hereda los de la plantilla. */
  readonly templateInheritHint = computed(
    () =>
      !this.isEditing() &&
      !!this.form.controls.based_on_role_id.value &&
      this.selectedCount() === 0,
  );
  readonly selectedCount = computed(() => this.selectedPermissions().size);

  ngOnInit(): void {
    const editing = this.editing();
    if (editing) {
      this.form.patchValue({ name: editing.name, display_name: editing.displayName });
      this.selectedPermissions.set(new Set(editing.permissions));
    }
  }

  fieldError(fieldName: string): string | null {
    const ctrl = this.form.get(fieldName);
    if (!ctrl || !ctrl.touched || ctrl.valid) return null;
    if (ctrl.hasError('required')) return 'Requerido';
    return 'Mínimo 2 caracteres';
  }

  /** Al elegir una plantilla: hereda sus permisos y sugiere el display name. */
  onTemplateChange(event: Event): void {
    const templateId = (event.target as HTMLSelectElement).value;
    const template = this.templates().find((t) => t.id === templateId);
    if (!template) return;
    this.selectedPermissions.set(new Set(template.permissions));
    if (!this.form.get('display_name')?.value) {
      this.form.patchValue({ display_name: template.displayName });
    }
  }

  isSelected(code: string): boolean {
    return this.selectedPermissions().has(code);
  }

  togglePermission(code: string, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.selectedPermissions.update((set) => {
      const next = new Set(set);
      if (checked) next.add(code);
      else next.delete(code);
      return next;
    });
  }

  groupAllSelected(group: PermissionGroup): boolean {
    return group.permissions.every((p) => this.selectedPermissions().has(p.code));
  }

  groupPartialSelected(group: PermissionGroup): boolean {
    const selected = group.permissions.filter((p) => this.selectedPermissions().has(p.code)).length;
    return selected > 0 && selected < group.permissions.length;
  }

  toggleGroup(group: PermissionGroup, event: Event): void {
    // Con estado parcial, un clic debe SELECCIONAR todo (no desmarcar todo).
    const checked = this.groupPartialSelected(group)
      ? true
      : (event.target as HTMLInputElement).checked;
    this.selectedPermissions.update((set) => {
      const next = new Set(set);
      for (const perm of group.permissions) {
        if (checked) next.add(perm.code);
        else next.delete(perm.code);
      }
      return next;
    });
  }

  submit(): void {
    if (this.saving()) return;
    this.form.get('name')?.markAsTouched();
    if (!this.isEditing() && this.form.controls.name.invalid) return;

    const propId = this.propCtx.currentPropId();
    if (!propId) {
      this.submitError.set('No hay propiedad seleccionada.');
      return;
    }

    const permissions = [...this.selectedPermissions()];
    const displayName = this.form.controls.display_name.value.trim();
    const editing = this.editing();

    this.saving.set(true);
    this.submitError.set(null);

    const request = editing
      ? this.api.updateRole(propId, editing.id, { display_name: displayName, permissions })
      : this.api.createRole(propId, {
          name: this.form.controls.name.value.trim(),
          display_name: displayName,
          permissions,
          based_on_role_id: this.form.controls.based_on_role_id.value || null,
        });

    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.saving.set(false);
        this.saved.emit();
      },
      error: (err: unknown) => {
        this.saving.set(false);
        // El backend devuelve 400/409 con `detail` en español (permisos desconocidos,
        // anti-lockout, self-lockout, duplicado…) — se muestra tal cual.
        this.submitError.set(this.errorMessage(err, editing ? 'Error al guardar el rol.' : 'Error al crear el rol.'));
      },
    });
  }

  private errorMessage(err: unknown, fallback: string): string {
    // getErrorMessage cubre HttpErrorResponse (tests) y ApiError del interceptor (vivo).
    return getErrorMessage(err) || fallback;
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
