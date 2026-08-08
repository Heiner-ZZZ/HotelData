import { httpResource } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { permissionDiff, templatePermissionDiff, type PermissionDiff } from '../../models/hotel-permissions.audit';
import type { RoleAuditDto } from '../../models/hotel-permissions.dto';
import type { HotelRole, RoleAuditEntry, RoleTemplate } from '../../models/hotel-permissions.model';
import { mapRoleAudit } from '../../services/hotel-permissions-api.service';

/** Meta de cada acción del historial (icono Material Symbols + etiqueta). */
const ACTION_META: Record<string, { label: string; icon: string }> = {
  create: { label: 'Creación', icon: 'add_circle' },
  update: { label: 'Actualización', icon: 'edit' },
  delete: { label: 'Eliminación', icon: 'delete' },
};

const DIFF_FIELD_LABELS: Record<string, string> = {
  display_name: 'Nombre visible',
  is_active: 'Estado',
};

@Component({
  selector: 'app-role-audit-modal',
  imports: [LoadingStateComponent, EmptyStateComponent],
  templateUrl: './role-audit-modal.html',
  styleUrl: './role-audit-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoleAuditModalComponent {
  readonly role = input.required<HotelRole>();
  readonly propId = input.required<number>();
  /** Plantillas clonables — para el diff "vs plantilla" cuando no hay historial. */
  readonly templates = input<RoleTemplate[]>([]);

  readonly close = output<void>();

  readonly auditResource = httpResource<RoleAuditDto>(() => {
    const pid = this.propId();
    const role = this.role();
    if (!pid || !role.id) return undefined;
    return `/api/management/hotels/${pid}/roles/${role.id}/audit`;
  });

  readonly audit = computed(() => {
    const raw = this.auditResource.value();
    return raw ? mapRoleAudit(raw) : null;
  });

  readonly isLoading = computed(() => this.auditResource.isLoading());
  readonly hasError = computed(() => !!this.auditResource.error());

  readonly noHistory = computed(() => {
    const a = this.audit();
    return a !== null && a.entries.length === 0;
  });

  /** Diff del rol actual vs su plantilla base (solo cuando no hay historial). */
  readonly templateDiff = computed<PermissionDiff | null>(() =>
    templatePermissionDiff(this.role(), this.templates()),
  );

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.close.emit();
    }
  }

  // ── Helpers de render ──

  actionLabel(action: string): string {
    return ACTION_META[action]?.label ?? action;
  }

  actionIcon(action: string): string {
    return ACTION_META[action]?.icon ?? 'history';
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString('es', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  /** Diff de permisos de una entrada (null si la entrada no tocó permisos). */
  readonly permissionDiff = permissionDiff;

  /** Diffs no relacionados a permisos (nombre visible, estado). */
  fieldDiffs(entry: RoleAuditEntry): { field: string; old: string; new: string }[] {
    const diff = entry.diff;
    if (!diff) return [];
    const out: { field: string; old: string; new: string }[] = [];
    for (const key of ['display_name', 'is_active']) {
      const f = diff[key];
      if (!f) continue;
      out.push({
        field: DIFF_FIELD_LABELS[key] ?? key,
        old: this.formatValue(f.old),
        new: this.formatValue(f.new),
      });
    }
    return out;
  }

  private formatValue(value: unknown): string {
    if (typeof value === 'boolean') return value ? 'Activo' : 'Inactivo';
    if (typeof value === 'string') return value || '—';
    if (Array.isArray(value)) return `${value.length} permiso(s)`;
    if (value === null || value === undefined) return '—';
    return String(value);
  }
}
