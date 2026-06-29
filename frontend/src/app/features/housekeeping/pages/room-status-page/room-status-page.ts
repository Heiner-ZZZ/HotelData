import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, computed, effect, inject, signal,
} from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { lastValueFrom } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { HousekeepingApiService, type RoomStatusItem } from '../../services/housekeeping-api.service';

// ─────────────────────────────────────────────────────────
// 10 Statuses — Hotel Housekeeping Lifecycle
// ─────────────────────────────────────────────────────────

export interface StatusDef {
  value: string;
  label: string;
  color: string;
  icon: string;
}

const STATUS_DEFS: StatusDef[] = [
  { value: 'vacant_dirty',          label: 'Vacante Sucia',           color: '#92400e', icon: 'report' },
  { value: 'vacant_clean',          label: 'Vacante Limpia',          color: '#16a34a', icon: 'check_circle' },
  { value: 'occupied_clean',        label: 'Ocupada Limpia',          color: '#006076', icon: 'bed' },
  { value: 'occupied_dirty',        label: 'Ocupada Sucia',           color: '#d97706', icon: 'bed' },
  { value: 'cleaning_in_progress',  label: 'Limpieza en Progreso',    color: '#ca8a04', icon: 'cleaning_services' },
  { value: 'cleaning_completed',    label: 'Limpieza Completada',     color: '#059669', icon: 'cleaning_services' },
  { value: 'inspected',             label: 'Inspeccionada',           color: '#4338ca', icon: 'fact_check' },
  { value: 'out_of_service',        label: 'Fuera de Servicio',       color: '#6f797d', icon: 'block' },
  { value: 'out_of_order',          label: 'Fuera de Orden',          color: '#ba1a1a', icon: 'dangerous' },
  { value: 'maintenance_requested', label: 'Mantenimiento Solicitado', color: '#ea580c', icon: 'build' },
];

const STATUS_COLORS: Record<string, string> = {};
const STATUS_ICONS: Record<string, string> = {};
for (const s of STATUS_DEFS) {
  STATUS_COLORS[s.value] = s.color;
  STATUS_ICONS[s.value] = s.icon;
}

// ── State machine: valid next statuses per current status ──
const NEXT_STATUSES: Record<string, string[]> = {
  vacant_dirty:          ['cleaning_in_progress', 'maintenance_requested'],
  vacant_clean:          ['occupied_clean', 'cleaning_in_progress'],
  occupied_clean:        ['occupied_dirty', 'vacant_dirty'],
  occupied_dirty:        ['cleaning_in_progress', 'vacant_dirty'],
  cleaning_in_progress:  ['cleaning_completed', 'maintenance_requested'],
  cleaning_completed:    ['inspected', 'cleaning_in_progress', 'maintenance_requested'],
  inspected:             ['vacant_clean', 'occupied_clean', 'maintenance_requested'],
  out_of_service:        ['inspected', 'cleaning_in_progress'],
  out_of_order:          ['inspected', 'maintenance_requested'],
  maintenance_requested: ['out_of_service', 'out_of_order', 'inspected'],
};

// ── Contextual quick actions per status ──
interface QuickAction {
  id: string;
  label: string;
  icon: string;
  variant: 'primary' | 'warning' | 'danger' | 'neutral';
  actionType: 'startCleaning' | 'completeCleaning' | 'approveCleaning' | 'statusChange' | 'reportMaintenance' | 'checkOut';
  targetStatus?: string;
  description: string;
}

function getQuickActions(status: string): QuickAction[] {
  switch (status) {
    case 'vacant_dirty':
      return [
        { id: 'startClean', label: 'Iniciar Limpieza', icon: 'cleaning_services', variant: 'warning', actionType: 'startCleaning', description: 'cleaning_in_progress' },
        { id: 'reqMaint', label: 'Solicitar Mantenimiento', icon: 'build', variant: 'danger', actionType: 'reportMaintenance', targetStatus: 'maintenance_requested', description: 'maintenance_requested' },
      ];
    case 'vacant_clean':
      return [
        { id: 'occupy', label: 'Ocupar', icon: 'bed', variant: 'primary', actionType: 'statusChange', targetStatus: 'occupied_clean', description: 'occupied_clean' },
        { id: 'startClean', label: 'Pre-limpieza', icon: 'cleaning_services', variant: 'warning', actionType: 'startCleaning', description: 'cleaning_in_progress' },
      ];
    case 'occupied_clean':
      return [
        { id: 'checkout', label: 'Check-out', icon: 'logout', variant: 'warning', actionType: 'checkOut', targetStatus: 'vacant_dirty', description: 'vacant_dirty' },
        { id: 'dirty', label: 'Reportar Sucia', icon: 'report', variant: 'danger', actionType: 'statusChange', targetStatus: 'occupied_dirty', description: 'occupied_dirty' },
      ];
    case 'occupied_dirty':
      return [
        { id: 'startClean', label: 'Iniciar Limpieza', icon: 'cleaning_services', variant: 'warning', actionType: 'startCleaning', description: 'cleaning_in_progress' },
        { id: 'checkout', label: 'Check-out', icon: 'logout', variant: 'neutral', actionType: 'checkOut', targetStatus: 'vacant_dirty', description: 'vacant_dirty' },
      ];
    case 'cleaning_in_progress':
      return [
        { id: 'completeClean', label: 'Completar Limpieza', icon: 'done', variant: 'primary', actionType: 'completeCleaning', description: 'cleaning_completed' },
        { id: 'reportDamage', label: 'Reportar Daño', icon: 'report', variant: 'danger', actionType: 'completeCleaning', description: 'Daño encontrado → mantenimiento' },
      ];
    case 'cleaning_completed':
      return [
        { id: 'inspect', label: 'Inspeccionar', icon: 'fact_check', variant: 'primary', actionType: 'approveCleaning', targetStatus: 'vacant_clean', description: 'vacant_clean' },
        { id: 'rewash', label: 'Re-lavado', icon: 'cleaning_services', variant: 'warning', actionType: 'startCleaning', description: 'cleaning_in_progress' },
        { id: 'reqMaint', label: 'Solicitar Mantenimiento', icon: 'build', variant: 'danger', actionType: 'reportMaintenance', targetStatus: 'maintenance_requested', description: 'maintenance_requested' },
      ];
    case 'inspected':
      return [
        { id: 'release', label: 'Liberar', icon: 'check_circle', variant: 'primary', actionType: 'approveCleaning', targetStatus: 'vacant_clean', description: 'vacant_clean' },
        { id: 'occupy', label: 'Ocupar', icon: 'bed', variant: 'primary', actionType: 'statusChange', targetStatus: 'occupied_clean', description: 'occupied_clean' },
        { id: 'reqMaint', label: 'Solicitar Mantenimiento', icon: 'build', variant: 'danger', actionType: 'reportMaintenance', targetStatus: 'maintenance_requested', description: 'maintenance_requested' },
      ];
    case 'out_of_service':
      return [
        { id: 'repair', label: 'Reparado', icon: 'verified', variant: 'primary', actionType: 'statusChange', targetStatus: 'inspected', description: 'inspected' },
        { id: 'startClean', label: 'Iniciar Limpieza', icon: 'cleaning_services', variant: 'warning', actionType: 'startCleaning', description: 'cleaning_in_progress' },
      ];
    case 'out_of_order':
      return [
        { id: 'repair', label: 'Reparado', icon: 'verified', variant: 'primary', actionType: 'statusChange', targetStatus: 'inspected', description: 'inspected' },
        { id: 'reqMaint', label: 'Solicitar Mantenimiento', icon: 'build', variant: 'danger', actionType: 'reportMaintenance', targetStatus: 'maintenance_requested', description: 'maintenance_requested' },
      ];
    case 'maintenance_requested':
      return [
        { id: 'outService', label: 'En Reparación', icon: 'construction', variant: 'neutral', actionType: 'statusChange', targetStatus: 'out_of_service', description: 'out_of_service' },
        { id: 'outOrder', label: 'Fuera de Orden', icon: 'dangerous', variant: 'danger', actionType: 'statusChange', targetStatus: 'out_of_order', description: 'out_of_order' },
        { id: 'repairDone', label: 'Reparado - Inspeccionar', icon: 'verified', variant: 'primary', actionType: 'statusChange', targetStatus: 'inspected', description: 'inspected' },
      ];
    default:
      return [];
  }
}

// ── Component ──

@Component({
  selector: 'app-room-status-page',
  imports: [DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PropertySelectorComponent],
  templateUrl: './room-status-page.html',
  styleUrl: './room-status-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoomStatusPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── Reactive route params ──
  private readonly queryParams = toSignal(this.route.queryParamMap);

  private readonly page = computed(() => Number(this.queryParams()?.get('page') ?? '1'));
  readonly statusFilter = computed(() => this.queryParams()?.get('status') ?? '');
  private readonly propId = computed(() => Number(this.queryParams()?.get('prop_id') ?? '0'));
  private readonly propLabel = computed(() => this.queryParams()?.get('prop_label') ?? '');

  readonly statusOptions = STATUS_DEFS;
  readonly statusColors = STATUS_COLORS;
  readonly statusIcons = STATUS_ICONS;

  readonly toast = signal<{ type: 'success' | 'error'; message: string } | null>(null);

  /** Track which rows are currently saving (by room id). */
  readonly savingRow = signal<Set<string>>(new Set());

  // ── Resource: fetch room statuses ──
  readonly resource = rxResource({
    request: () => ({
      page: this.page(),
      status: this.statusFilter(),
      propId: this.propId(),
      propLabel: this.propLabel(),
    }),
    loader: async ({ request }) => {
      const { page, status, propId } = request;
      if (!propId) {
        return await lastValueFrom(this.api.getRoomStatus(undefined, status || undefined, page));
      }
      await lastValueFrom(this.api.syncRoomStatus(propId));
      return await lastValueFrom(this.api.getRoomStatus(propId, status || undefined, page));
    },
  });

  /** Side-effect: sync property context when propId changes */
  private readonly _syncPropCtx = effect(() => {
    const pid = this.propId();
    if (pid) {
      this.propertyCtx.setProperty(pid, this.propLabel() || `Propiedad #${pid}`);
    } else {
      this.propertyCtx.clear();
    }
  });

  readonly data = computed(() => this.resource.value() ?? null);
  readonly viewState = computed<'loading' | 'error' | 'empty' | 'success'>(() => {
    const s = this.resource.status();
    if (s === 'loading' || s === 'idle') return 'loading';
    if (s === 'error') return 'error';
    const d = this.data();
    if (!d || !d.items.length) return 'empty';
    return 'success';
  });

  // ── Helpers ──

  getStatusLabel(status: string): string {
    return STATUS_DEFS.find((s) => s.value === status)?.label ?? status;
  }

  getStatusColor(status: string): string {
    return STATUS_COLORS[status] ?? '#6f797d';
  }

  getStatusIcon(status: string): string {
    return STATUS_ICONS[status] ?? 'circle';
  }

  getStatusNext(status: string): string[] {
    return NEXT_STATUSES[status] ?? [];
  }

  getActions(status: string): QuickAction[] {
    return getQuickActions(status);
  }

  getActionLabel(action: QuickAction, item: RoomStatusItem): string {
    switch (action.actionType) {
      case 'startCleaning': return item.status === 'vacant_dirty' || item.status === 'occupied_dirty'
        ? '🧹 Iniciar Limpieza' : '🔄 Re-lavado';
      case 'completeCleaning': return action.id === 'reportDamage' ? '🔧 Reportar Daño' : '✅ Completar';
      case 'approveCleaning': return item.status === 'cleaning_completed' ? '🔍 Inspeccionar' : '✅ Liberar';
      case 'checkOut': return '🚪 Check-out';
      case 'reportMaintenance': return '🔧 Solicitar Mantenimiento';
      case 'statusChange': {
        const map: Record<string, string> = {
          occupied_clean: '🏨 Ocupar',
          vacant_dirty: '🚪 Check-out',
          occupied_dirty: '🔴 Sucia',
          inspected: '🔍 Reparado - Inspeccionar',
          out_of_service: '🛠️ En Reparación',
          out_of_order: '⛔ Fuera de Orden',
          maintenance_requested: '🔧 Solicitar Mtto',
          vacant_clean: '✅ Liberar',
          cleaning_in_progress: '🧹 Iniciar Limpieza',
        };
        return map[action.targetStatus ?? ''] ?? action.label;
      }
      default: return action.label;
    }
  }

  // ── Inline Status Change (direct via upsert) ──

  async updateStatusInline(item: RoomStatusItem, newStatus: string): Promise<void> {
    if (newStatus === item.status) return;
    const id = item.id;
    this.savingRow.update((set) => { const n = new Set(set); n.add(id); return n; });
    this.toast.set(null);

    try {
      await lastValueFrom(this.api.upsertRoomStatus({
        prop_id: item.propId,
        room_type_id: item.roomTypeId,
        room_label: item.roomLabel,
        status: newStatus,
        note: item.note || undefined,
      }));
      this.toast.set({ type: 'success', message: `Hab. ${item.roomLabel} → ${this.getStatusLabel(newStatus)}` });
      this.resource.reload();
    } catch {
      this.toast.set({ type: 'error', message: `Error al actualizar Hab. ${item.roomLabel}` });
    } finally {
      this.savingRow.update((set) => { const n = new Set(set); n.delete(id); return n; });
    }
  }

  // ── Quick Actions ──

  async executeAction(item: RoomStatusItem, action: QuickAction): Promise<void> {
    const id = item.id;
    this.savingRow.update((set) => { const n = new Set(set); n.add(id); return n; });
    this.toast.set(null);

    try {
      switch (action.actionType) {
        case 'startCleaning': {
          await lastValueFrom(this.api.startCleaning(item.propId, item.roomLabel, ''));
          this.toast.set({ type: 'success', message: `🧹 Limpieza iniciada — Hab. ${item.roomLabel}` });
          break;
        }
        case 'completeCleaning': {
          const hasDamage = action.id === 'reportDamage';
          await lastValueFrom(this.api.completeCleaning({
            prop_id: item.propId,
            room_label: item.roomLabel,
            assigned_to: '',
            observations: hasDamage ? '' : 'Limpieza completada',
            damage_found: hasDamage,
            damage_description: hasDamage ? 'Daño reportado durante limpieza' : '',
            needs_maintenance: false,
          }));
          this.toast.set({
            type: 'success',
            message: hasDamage
              ? `🔧 Daño reportado — Hab. ${item.roomLabel}`
              : `✅ Limpieza completada — Hab. ${item.roomLabel}`,
          });
          break;
        }
        case 'approveCleaning': {
          const setOccupied = action.targetStatus === 'occupied_clean';
          await lastValueFrom(this.api.approveCleaning(
            item.propId, item.roomLabel, 'supervisor', '',
            setOccupied,
          ));
          this.toast.set({
            type: 'success',
            message: setOccupied
              ? `🏨 Hab. ${item.roomLabel} ocupada`
              : `✅ Hab. ${item.roomLabel} liberada`,
          });
          break;
        }
        case 'checkOut': {
          await lastValueFrom(this.api.upsertRoomStatus({
            prop_id: item.propId,
            room_type_id: item.roomTypeId,
            room_label: item.roomLabel,
            status: 'vacant_dirty',
            note: 'Check-out',
          }));
          this.toast.set({ type: 'success', message: `🚪 Check-out — Hab. ${item.roomLabel}` });
          break;
        }
        case 'reportMaintenance': {
          await lastValueFrom(this.api.upsertRoomStatus({
            prop_id: item.propId,
            room_type_id: item.roomTypeId,
            room_label: item.roomLabel,
            status: 'maintenance_requested',
            note: 'Mantenimiento solicitado',
          }));
          this.toast.set({ type: 'success', message: `🔧 Mantenimiento solicitado — Hab. ${item.roomLabel}` });
          break;
        }
        case 'statusChange': {
          if (action.targetStatus) {
            await lastValueFrom(this.api.upsertRoomStatus({
              prop_id: item.propId,
              room_type_id: item.roomTypeId,
              room_label: item.roomLabel,
              status: action.targetStatus,
              note: action.label,
            }));
            this.toast.set({
              type: 'success',
              message: `${action.label} — Hab. ${item.roomLabel}`,
            });
          }
          break;
        }
      }
      this.resource.reload();
    } catch {
      this.toast.set({ type: 'error', message: `Error en acción para Hab. ${item.roomLabel}` });
    } finally {
      this.savingRow.update((set) => { const n = new Set(set); n.delete(id); return n; });
    }
  }

  // ── Filter / Navigation ──

  setStatusFilter(status: string): void {
    const newStatus = status === this.statusFilter() ? '' : status;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        page: null,
        status: newStatus || null,
        prop_id: this.propId() || null,
        prop_label: this.propLabel() || null,
      },
    });
  }

  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: page > 1 ? page : null },
      queryParamsHandling: 'merge',
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        prop_id: event.propId || null,
        prop_label: label || null,
        status: this.statusFilter() || null,
        page: null,
      },
    });
  }

  getNextStatuses(status: string): string[] {
    return NEXT_STATUSES[status] ?? [];
  }
}
