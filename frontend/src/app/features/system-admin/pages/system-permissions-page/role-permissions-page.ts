import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';

import { ConfirmDialogComponent } from '../../../../shared/ui/confirm-dialog/confirm-dialog.component';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { ToastService } from '../../../../shared/services/toast.service';
import { OperationModeService, type OperationMode } from '../../../../core/services/operation-mode.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { RoleDetailResponseDto } from '../../models/system-permissions.dto';
import type { NavigationItem, RoleDetailModel } from '../../models/system-permissions.model';
import { mapRoleDetailResponse } from '../../mappers/system-permissions.mapper';
import {
  computeNavVisibility,
  countSectionCodesWithHidden,
  filterResourcesByQuery,
  isMatrixVisibleCode,
  MATRIX_BASE_ACTIONS,
  MATRIX_CONDITIONAL_ACTIONS,
  matrixActionColumns,
  matrixHiddenCodes,
  sectionForNavItem,
  sectionForResource,
  SECTION_DEFS,
  type SectionKey,
  type ResourceActionsRow,
} from '../../models/role-permission-sections';
import { SystemPermissionsApiService } from '../../services/system-permissions-api.service';
import { SystemPermissionsContextService } from '../../services/system-permissions-context.service';

type CrudAction = 'manage' | 'create' | 'read' | 'update' | 'delete' | 'execute' | 'moderate';
/** Columnas base SIEMPRE visibles, en este orden (fuente única: modelo puro). */
const BASE_ACTIONS: readonly CrudAction[] = MATRIX_BASE_ACTIONS;
/** Acciones CONDICIONALES (``execute``/``moderate``): la columna se dibuja SOLO
 *  si algún recurso del catálogo la tiene. Si ningún permiso de la matriz
 *  ofrece la opción, la columna desaparece en vez de quedar vacía. */
const EXTRA_ACTIONS: readonly CrudAction[] = MATRIX_CONDITIONAL_ACTIONS;
/** Todas las acciones que la matriz reconoce (base + condicionales), como
 *  lista para el predicado compartido ``isMatrixVisibleCode`` (misma fuente
 *  que ``matrixHiddenCodes`` — sin drift entre visible y oculto). */
const KNOWN_ACTIONS: readonly CrudAction[] = [...BASE_ACTIONS, ...EXTRA_ACTIONS];

interface CrudPermission {
  code: string;
  description: string;
}

interface CrudResourceRow extends ResourceActionsRow {
  actions: Partial<Record<CrudAction, CrudPermission>>;
}

interface PermissionSectionModel {
  key: SectionKey;
  title: string;
  icon: string;
  resources: CrudResourceRow[];
  /** Códigos del catálogo que la matriz no dibuja (compuestos/approve/…). */
  hiddenCodes: CrudPermission[];
  navItems: NavigationItem[];
}

@Component({
  selector: 'app-role-permissions-page',
  standalone: true,
  imports: [ConfirmDialogComponent, ErrorStateComponent, LoadingStateComponent, RouterLink],
  template: `
    <app-confirm-dialog />
    <section class="permissions-subpage role-detail-page">
      @if (detailResource.isLoading()) {
        <app-loading-state label="Cargando detalle del rol..." />
      } @else if (detailResource.error()) {
        <app-error-state title="No fue posible cargar el rol" description="Revisa el nombre del rol o vuelve a la lista de roles." />
      } @else if (detailResource.value(); as detail) {
        <div class="role-detail-header">
          <div>
            <a class="back-link" routerLink="../">
              <span class="material-symbols-outlined">arrow_back</span> Volver a roles
            </a>
            <div class="role-detail-title-row">
              <span class="editor-badge">{{ detail.role.roleName }}</span>
              <span class="editor-subtitle">{{ selectedCodes().length }} permisos asignados</span>
            </div>
          </div>
          <button type="button" class="btn btn-sm btn-danger" (click)="closeEditor()">
            <span class="material-symbols-outlined">close</span> Cerrar
          </button>
        </div>

        <div class="editor-body editor-body--stacked">
          <div class="editor-perms">
            <div class="field">
              <label class="field-label" for="role-description">Descripción del rol</label>
              <textarea id="role-description" class="field-input" [value]="description()" (input)="description.set($any($event.target).value)" rows="2"></textarea>
            </div>

            <div class="editor-perms-header">
              <span class="field-label">Permisos — Matriz CRUD</span>
              <span class="perm-count">{{ selectedCodes().length }} / {{ detail.permissions.length }} seleccionados</span>
              <label class="matrix-search" [class.has-value]="matrixFilter()">
                <span class="material-symbols-outlined matrix-search-icon">search</span>
                <input
                  type="search"
                  class="matrix-search-input"
                  placeholder="Filtrar por recurso o código…"
                  aria-label="Filtrar la matriz de permisos"
                  [value]="matrixFilter()"
                  (input)="matrixFilter.set($any($event.target).value)"
                />
                @if (matrixFilter()) {
                  <button type="button" class="matrix-search-clear" (click)="matrixFilter.set('')" aria-label="Limpiar filtro">
                    <span class="material-symbols-outlined">close</span>
                  </button>
                }
              </label>
            </div>

            @if (matrixFilter().trim() && filteredSections().length === 0) {
              <div class="matrix-empty">
                <span class="material-symbols-outlined">search_off</span>
                <p>Sin recursos que coincidan con «{{ matrixFilter() }}».</p>
              </div>
            }

            @if (matrixSummary().hidden > 0) {
              <p class="matrix-summary-hint">
                <span class="material-symbols-outlined">tune</span>
                {{ matrixSummary().visible }} en la matriz CRUD + {{ matrixSummary().hidden }} compuestos (fuera de la matriz) = {{ detail.permissions.length }} del catálogo. Los compuestos se muestran como chips en su sección.
              </p>
            }

            <p class="subpage-hint">
              <span class="material-symbols-outlined">account_tree</span>
              Permisos agrupados por menú. Activa una sección para ver su vista previa de navegación.
            </p>

            @for (section of filteredSections(); track section.key) {
              <section class="perm-section" [class.is-collapsed]="collapsedSections().has(section.key)">
                <button type="button" class="perm-section-head" (click)="toggleSection(section.key)" [attr.aria-expanded]="!collapsedSections().has(section.key)">
                  <span class="material-symbols-outlined perm-section-icon">{{ section.icon }}</span>
                  <span class="perm-section-title">{{ section.title }}</span>
                  <span class="perm-section-counts">
                    <span class="perm-section-codes" title="Permisos seleccionados / totales de la sección. El total incluye los códigos compuestos (fuera de la matriz) que se muestran como chips debajo de la tabla.">{{ section.key }} · {{ sectionSelectedCount(section.key) }}/{{ sectionTotalCount(section.key) }}</span>
                    @if (section.navItems.length) { · {{ section.navItems.length }} ítems de menú }
                  </span>
                  <span class="material-symbols-outlined perm-chevron">expand_more</span>
                </button>

                @if (!collapsedSections().has(section.key)) {
                  <div class="perm-section-body" [class.perm-section-body--split]="section.navItems.length > 0">
                    <div class="crud-matrix-wrap crud-matrix-wrap--section">
                      @if (section.resources.length > 0) {
                      <table class="crud-matrix-table">
                        <thead>
                          <tr>
                            <th class="crud-resource-th">Recurso</th>
                            @for (action of sectionActionColumns(section); track action) { <th class="crud-action-th">{{ action }}</th> }
                          </tr>
                        </thead>
                        <tbody>
                          @for (row of section.resources; track row.resource) {
                            <tr class="crud-row" [class.crud-row--partial]="isPartiallySelected(row.resource)">
                              <td class="crud-resource-td"><span class="crud-resource-name">{{ row.resource }}</span></td>
                              <td class="crud-check-td">
                                @if (row.actions.manage) {
                                  <label class="crud-check" [class.crud-check--partial]="isPartiallySelected(row.resource)">
                                    <input type="checkbox" [checked]="isFullySelected(row.resource)" [indeterminate]="isPartiallySelected(row.resource)" [disabled]="!hasReadPermission(row.resource)" (change)="toggleResource(row.resource)" />
                                    <span class="crud-check-label">manage</span>
                                  </label>
                                } @else { <span class="crud-empty">—</span> }
                              </td>
                              @for (action of sectionActionColumns(section); track action) {
                                @if (action !== 'manage') {
                                  <td class="crud-check-td">
                                    @if (row.actions[action]; as permission) {
                                      <label class="crud-check">
                                        <input type="checkbox" [checked]="selectedCodes().includes(permission.code)" [disabled]="action !== 'read' && !hasReadPermission(row.resource)" (change)="togglePermission(permission.code)" />
                                      </label>
                                    } @else { <span class="crud-empty">—</span> }
                                  </td>
                                }
                              }
                            </tr>
                          }
                        </tbody>
                      </table>
                      }

                      @if (section.hiddenCodes.length > 0) {
                        <div class="hidden-codes" [class.is-open]="hiddenCodesOpen().has(section.key)">
                          <button type="button" class="hidden-codes-toggle" (click)="toggleHiddenCodes(section.key)" [attr.aria-expanded]="hiddenCodesOpen().has(section.key)">
                            <span class="material-symbols-outlined hidden-codes-icon">tune</span>
                            <span class="hidden-codes-label">Códigos compuestos (fuera de la matriz)</span>
                            <span class="hidden-codes-count">{{ hiddenChipsSelected(section.hiddenCodes) }}/{{ section.hiddenCodes.length }} asignados</span>
                            <span class="material-symbols-outlined perm-chevron">expand_more</span>
                          </button>
                          @if (hiddenCodesOpen().has(section.key)) {
                            <div class="hidden-codes-chips">
                              @for (perm of section.hiddenCodes; track perm.code) {
                                <button
                                  type="button"
                                  class="hidden-chip"
                                  [class.is-selected]="selectedCodes().includes(perm.code)"
                                  [title]="perm.description || perm.code"
                                  (click)="toggleHiddenPermission(perm.code)"
                                >
                                  <span class="material-symbols-outlined hidden-chip-icon">{{ selectedCodes().includes(perm.code) ? 'check_circle' : 'add_circle' }}</span>
                                  <span class="hidden-chip-code">{{ perm.code }}</span>
                                </button>
                              }
                            </div>
                          }
                        </div>
                      }
                    </div>

                    @if (section.navItems.length > 0) {
                      <div class="section-preview" [class.is-open]="openPreviews().has(section.key)">
                        <button type="button" class="section-preview-toggle" (click)="togglePreview(section.key)" [attr.aria-expanded]="openPreviews().has(section.key)">
                          <span class="material-symbols-outlined section-preview-icon">visibility</span>
                          <span>Vista previa de navegación</span>
                          <span class="section-preview-count">{{ sectionVisibleCount(section.key) }}/{{ section.navItems.length }} visibles</span>
                          <span class="material-symbols-outlined perm-chevron">expand_more</span>
                        </button>
                        @if (openPreviews().has(section.key)) {
                          <div class="nav-preview-list">
                            @for (item of section.navItems; track item.slug) {
                              <div class="nav-item" [class.is-header]="item.nodeType === 'container'" [class.visible]="isItemVisible(item)" [class.hidden]="!isItemVisible(item)">
                                <span class="nav-icon material-symbols-outlined">{{ item.icon }}</span>
                                <span class="nav-label">{{ item.label }}</span>
                                @if (item.permissionCode) {
                                  <span class="nav-perm" [title]="'Requiere el permiso «' + item.permissionCode + '»'">{{ item.permissionCode }}</span>
                                }
                                <span class="nav-badge" [class.visible-badge]="isItemVisible(item)" [class.hidden-badge]="!isItemVisible(item)">{{ isItemVisible(item) ? 'Visible' : 'Oculto' }}</span>
                              </div>
                            }
                          </div>
                        }
                      </div>
                    }
                  </div>
                }
              </section>
            }

            <div class="editor-actions">
              <button type="button" class="btn btn-primary" [disabled]="saving()" (click)="saveRole()">
                @if (saving()) { <span class="material-symbols-outlined spinning">refresh</span> Guardando… }
                @else { <span class="material-symbols-outlined">save</span> Guardar cambios }
              </button>
            </div>
          </div>
        </div>
      }
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RolePermissionsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(SystemPermissionsApiService);
  private readonly context = inject(SystemPermissionsContextService);
  private readonly toast = inject(ToastService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly opMode = inject(OperationModeService);

  /** Modo del nav: esta página edita permisos → nunca "Solo lectura". El
   *  detalle lleva el nombre del rol para que el tooltip sea útil. */
  private readonly _opMode = computed<{ mode: OperationMode; detail: string }>(() => {
    const role = this.roleParam();
    return { mode: 'update', detail: role ? `Permisos · ${role}` : 'Permisos del rol' };
  });

  readonly roleName = toSignal(this.route.paramMap, { initialValue: this.route.snapshot.paramMap });
  readonly roleParam = computed(() => this.roleName().get('roleName') || '');
  readonly detailResource = httpResource<RoleDetailModel>(() => {
    const roleName = this.roleParam();
    return roleName ? `/api/admin/permissions/roles/${encodeURIComponent(roleName)}` : undefined;
  }, { parse: (dto) => mapRoleDetailResponse(dto as RoleDetailResponseDto) });

  readonly selectedCodes = signal<string[]>([]);
  readonly description = signal('');
  readonly saving = signal(false);

  /** Texto del buscador de la matriz (filtra recursos por nombre/código). */
  readonly matrixFilter = signal('');

  /** Secciones colapsadas de la matriz (por defecto todas abiertas). */
  readonly collapsedSections = signal<Set<string>>(new Set());
  /** Previews de navegación abiertos (por defecto todos cerrados). */
  readonly openPreviews = signal<Set<string>>(new Set());
  /** Bloques de "códigos compuestos" abiertos (por defecto cerrados). */
  readonly hiddenCodesOpen = signal<Set<string>>(new Set());

  /** Recurso → acciones del catálogo (para la matriz CRUD). */
  readonly resourceRows = computed(() => {
    const rows = new Map<string, Partial<Record<CrudAction, CrudPermission>>>();
    for (const permission of this.detailResource.value()?.permissions ?? []) {
      if (!isMatrixVisibleCode(permission.permissionCode, KNOWN_ACTIONS)) continue;
      const [resource, action] = permission.permissionCode.split('.', 2);
      const row = rows.get(resource) ?? {};
      row[action as CrudAction] = { code: permission.permissionCode, description: permission.description };
      rows.set(resource, row);
    }
    return rows;
  });

  /** Códigos ocultos de la matriz (compuestos/no-CRUD: ``properties.approve``,
   *  ``hotel.manage_roles``, ``inventory.products.cost.*``) agrupados por
   *  sección. Son la diferencia entre el total del catálogo y lo dibujable
   *  (87 visibles + 4 compuestos = 91), y se muestran como chips toggleables. */
  readonly hiddenCodesBySection = computed<Map<SectionKey, CrudPermission[]>>(() => {
    const bySection = new Map<SectionKey, CrudPermission[]>();
    const known = [...BASE_ACTIONS, ...EXTRA_ACTIONS];
    for (const permission of this.detailResource.value()?.permissions ?? []) {
      const item = { code: permission.permissionCode, description: permission.description };
      if (matrixHiddenCodes([item], known).length === 0) continue;
      const resource = item.code.split('.', 2)[0] ?? item.code;
      const key = sectionForResource(resource);
      if (!bySection.has(key)) bySection.set(key, []);
      bySection.get(key)!.push(item);
    }
    return bySection;
  });

  /** Resumen global de la matriz: visibles (checkboxes CRUD) vs compuestos
   *  (chips) para explicar por qué el total del catálogo supera lo dibujable
   *  (87 + 4 = 91 en super_admin). */
  readonly matrixSummary = computed<{ visible: number; hidden: number }>(() => {
    let visible = 0;
    for (const actions of this.resourceRows().values()) {
      visible += Object.values(actions).filter(Boolean).length;
    }
    let hidden = 0;
    for (const perms of this.hiddenCodesBySection().values()) hidden += perms.length;
    return { visible, hidden };
  });

  /** Visibilidad en vivo por nodo (top-down, una sola pasada por cambio de
   *  selección). Replica el pruning del server sin round-trip HTTP. */
  readonly visibleNavBySlug = computed(() => {
    const selected = this.selectedCodes();
    const navItems = this.detailResource.value()?.role.navigationCatalog ?? [];
    return computeNavVisibility(navItems, selected);
  });

  /** Secciones visibles tras aplicar el buscador: recursos y códigos ocultos
   *  filtrados por nombre/código/descripción; secciones sin coincidencias
   *  desaparecen (un chip compuesto puede mantener viva la sección). */
  readonly filteredSections = computed<PermissionSectionModel[]>(() => {
    const query = this.matrixFilter();
    const trimmed = query.trim();
    if (!trimmed) return this.sections();
    const q = trimmed.toLowerCase();
    return this.sections()
      .map((section) => ({
        ...section,
        resources: filterResourcesByQuery(section.resources, q),
        hiddenCodes: section.hiddenCodes.filter(
          (perm) =>
            perm.code.toLowerCase().includes(q) ||
            (perm.description ?? '').toLowerCase().includes(q),
        ),
      }))
      .filter((section) => section.resources.length > 0 || section.hiddenCodes.length > 0);
  });

  /** Columnas CRUD de UNA sección: base + extras presentes en los recursos de
   *  ESA sección. Si ninguna fila de la caja tiene ``execute``/``moderate``,
   *  esas columnas no se dibujan — antes eran globales: bastaba que existieran
   *  en cualquier parte del catálogo para aparecer vacías en todas las cajas. */
  sectionActionColumns(section: PermissionSectionModel): CrudAction[] {
    return matrixActionColumns(section.resources, BASE_ACTIONS, EXTRA_ACTIONS) as CrudAction[];
  }

  /** Secciones del sidebar con sus recursos y sus ítems de navegación. */
  readonly sections = computed<PermissionSectionModel[]>(() => {
    const rows = this.resourceRows();
    const hiddenBySection = this.hiddenCodesBySection();
    const navItems = (this.detailResource.value()?.role.navigationCatalog ?? [])
      // Las raíces (gestion/sistema/propietario/huesped) son estructurales
      // (sin href ni permiso): la agrupación por sección ya las representa.
      .filter((item) => item.parentSlug !== null);

    const navBySection = new Map<SectionKey, NavigationItem[]>();
    for (const item of navItems) {
      const key = sectionForNavItem(item);
      if (!navBySection.has(key)) navBySection.set(key, []);
      navBySection.get(key)!.push(item);
    }

    const resourcesBySection = new Map<SectionKey, CrudResourceRow[]>();
    for (const [resource, actions] of rows) {
      const key = sectionForResource(resource);
      if (!resourcesBySection.has(key)) resourcesBySection.set(key, []);
      resourcesBySection.get(key)!.push({ resource, actions });
    }

    return SECTION_DEFS.map((def) => ({
      key: def.key,
      title: def.title,
      icon: def.icon,
      resources: (resourcesBySection.get(def.key) ?? []).sort((a, b) => a.resource.localeCompare(b.resource)),
      hiddenCodes: hiddenBySection.get(def.key) ?? [],
      navItems: navBySection.get(def.key) ?? [],
    })).filter(
      (section) => section.resources.length > 0 || section.hiddenCodes.length > 0 || section.navItems.length > 0,
    );
  });

  constructor() {
    // El cleanup libera el transient anterior al cambiar de rol y al destruir
    // la página (mismo patrón que check-in/check-out detail).
    effect((onCleanup) => {
      const m = this._opMode();
      onCleanup(this.opMode.setTransientMode(m.mode, m.detail));
    });

    effect(() => {
      const detail = this.detailResource.value();
      if (!detail) return;
      this.selectedCodes.set(this.withReadDependencies(detail.role.permissionCodes));
      this.description.set(detail.role.description);
    }, { allowSignalWrites: true });
  }

  // ── Matriz CRUD ────────────────────────────────────────────────────

  isFullySelected(resource: string): boolean {
    const actions = this.resourceRows().get(resource);
    const codes = Object.values(actions ?? {}).filter(Boolean).map((permission) => permission!.code);
    return codes.length > 0 && codes.every((code) => this.selectedCodes().includes(code));
  }

  isPartiallySelected(resource: string): boolean {
    const actions = this.resourceRows().get(resource);
    const codes = Object.values(actions ?? {}).filter(Boolean).map((permission) => permission!.code);
    const count = codes.filter((code) => this.selectedCodes().includes(code)).length;
    return count > 0 && count < codes.length;
  }

  hasReadPermission(resource: string): boolean {
    return Boolean(this.resourceRows().get(resource)?.read);
  }

  toggleResource(resource: string): void {
    const wasFullySelected = this.isFullySelected(resource);
    const row = this.resourceRows().get(resource);
    if (!row || !this.hasReadPermission(resource)) {
      if (row && !this.hasReadPermission(resource)) {
        this.toast.warning(`No se puede asignar acciones de ${resource}: el catálogo no tiene ${resource}.read.`);
      }
      return;
    }
    const codes = Object.values(row).filter(Boolean).map((permission) => permission!.code);
    const selected = new Set(this.selectedCodes());
    if (codes.every((code) => selected.has(code))) {
      codes.forEach((code) => selected.delete(code));
    } else {
      codes.forEach((code) => selected.add(code));
      const readCode = row.read?.code;
      if (readCode) selected.add(readCode);
    }
    this.selectedCodes.set([...selected]);
  }

  togglePermission(code: string): void {
    const [resource, action] = code.split('.', 2);
    if (!resource || !action) return;

    const wasFullySelected = this.isFullySelected(resource);
    const selected = new Set(this.selectedCodes());
    if (selected.has(code)) {
      if (action === 'read' && this.hasOtherSelectedAction(resource)) {
        this.toast.warning(`El permiso ${resource}.read es obligatorio mientras haya otras acciones activas.`);
        return;
      }
      selected.delete(code);
    } else {
      if (action !== 'read' && !this.hasReadPermission(resource)) {
        this.toast.warning(`Primero debe existir ${resource}.read para activar ${action}.`);
        return;
      }
      selected.add(code);
      if (action !== 'read') {
        const readCode = this.resourceRows().get(resource)?.read?.code;
        if (readCode) selected.add(readCode);
      }
    }
    this.selectedCodes.set([...selected]);
  }

  private hasOtherSelectedAction(resource: string): boolean {
    const prefix = `${resource}.`;
    return this.selectedCodes().some(
      (selectedCode) => selectedCode.startsWith(prefix) && selectedCode !== `${resource}.read`,
    );
  }

  private withReadDependencies(codes: string[]): string[] {
    const normalized = new Set(codes);
    for (const code of codes) {
      const [resource, action] = code.split('.', 2);
      if (!resource || !action || action === 'read') continue;
      const readCode = this.resourceRows().get(resource)?.read?.code;
      if (readCode) normalized.add(readCode);
    }
    return [...normalized];
  }

  // ── Secciones y vista previa ───────────────────────────────────────

  toggleSection(key: string): void {
    this.collapsedSections.update((set) => {
      const next = new Set(set);
      if (next.has(key)) { next.delete(key); } else { next.add(key); }
      return next;
    });
  }

  togglePreview(key: string): void {
    this.openPreviews.update((set) => {
      const next = new Set(set);
      if (next.has(key)) { next.delete(key); } else { next.add(key); }
      return next;
    });
  }

  toggleHiddenCodes(key: string): void {
    this.hiddenCodesOpen.update((set) => {
      const next = new Set(set);
      if (next.has(key)) { next.delete(key); } else { next.add(key); }
      return next;
    });
  }

  /** Toggle de un código compuesto (chip): mismo contrato que la matriz — al
   *  activarlo arrastra su ``<resource>.read`` si el catálogo lo tiene. */
  toggleHiddenPermission(code: string): void {
    const selected = new Set(this.selectedCodes());
    if (selected.has(code)) {
      selected.delete(code);
    } else {
      selected.add(code);
      const resource = code.split('.', 2)[0] ?? '';
      const readCode = this.resourceRows().get(resource)?.read?.code;
      if (readCode) selected.add(readCode);
    }
    this.selectedCodes.set([...selected]);
  }

  sectionSelectedCount(key: SectionKey): number {
    const section = this.sections().find((item) => item.key === key);
    if (!section) return 0;
    return countSectionCodesWithHidden(section.resources, section.hiddenCodes, this.selectedCodes()).selected;
  }

  /** Total de códigos del catálogo de la sección (denominador del conteo).
   *  Incluye los compuestos/ocultos para que la suma de secciones cuadre con
   *  el total global del catálogo (87 visibles + 4 compuestos = 91). */
  sectionTotalCount(key: SectionKey): number {
    const section = this.sections().find((item) => item.key === key);
    if (!section) return 0;
    return countSectionCodesWithHidden(section.resources, section.hiddenCodes, this.selectedCodes()).total;
  }

  /** Seleccionados entre los chips compuestos de la sección (X/Y del bloque).
   *  Recibe la lista visible (ya filtrada por el buscador) para que el badge
   *  sea coherente con los chips renderizados bajo el filtro activo. */
  hiddenChipsSelected(codes: readonly { code: string }[]): number {
    return codes.filter((perm) => this.selectedCodes().includes(perm.code)).length;
  }

  isItemVisible(item: NavigationItem): boolean {
    return this.visibleNavBySlug().get(item.slug) ?? false;
  }

  sectionVisibleCount(key: SectionKey): number {
    const section = this.sections().find((item) => item.key === key);
    if (!section) return 0;
    return section.navItems.filter((item) => this.isItemVisible(item)).length;
  }

  // ── Guardar ────────────────────────────────────────────────────────

  async saveRole(): Promise<void> {
    const roleName = this.roleParam();
    if (!roleName) return;
    if (roleName === 'super_admin') {
      // El server rechaza la escritura de super_admin (bootstrap del sistema):
      // avisar con el toast global en vez de fallar en silencio.
      this.toast.warning('El rol super_admin no se modifica desde esta vista.');
      return;
    }
    const confirmed = await this.confirmDialog.open({
      title: 'Guardar cambios del rol',
      message: `¿Confirmas la actualización de permisos para el rol «${roleName}»?`,
      details: [`${this.selectedCodes().length} permisos seleccionados`, 'Los cambios afectarán a todos los usuarios con este rol.'],
      variant: 'warning',
      confirmLabel: 'Guardar cambios',
      cancelLabel: 'Cancelar',
    });
    if (!confirmed) return;
    this.saving.set(true);
    this.api.updateRole(roleName, { description: this.description(), permission_codes: [...this.selectedCodes()] }).subscribe({
      next: (res) => {
        this.toast.success(res.message);
        this.saving.set(false);
        this.context.overviewResource.reload();
        this.detailResource.reload();
      },
      error: (err: ApiError) => {
        this.toast.error(err.message || 'Error al guardar los permisos del rol.');
        this.saving.set(false);
      },
    });
  }

  closeEditor(): void {
    void this.router.navigate(['/system/permissions/roles']);
  }
}
