import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { httpResource } from '@angular/common/http';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { NgTemplateOutlet } from '@angular/common';
import { filter } from 'rxjs';
import type { Params } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { PropertyContextService, isGlobalManagementPath } from '../../../shared/services/property-context.service';

/** Flat wire node from ``GET /api/admin/navigation`` (camelCase, parent refs). */
interface NavigationItem {
  slug: string;
  parentSlug: string | null;
  position: number;
  nodeType: string | null;
  label: string;
  href: string | null;
  icon: string;
  visible: boolean;
  permissionId: string | null;
  permissionCode: string | null;
  horizontalMenu: boolean;
}

/** Tree node built client-side from the flat list. */
interface NavNode extends NavigationItem {
  children: NavNode[];
}

interface NavigationResponse {
  items: NavigationItem[];
}

/** Segmento de ruta que es un ID dinámico (reserva, detalle de entidad…). */
const DYNAMIC_ID_PATTERN = /^(BK-[\w-]+|[0-9a-f]{24}|\d+)$/i;

/**
 * Build an ordered tree from the flat backend node list (adjacency list).
 * Only ``visible`` nodes are kept — the backend already computes visibility
 * top-down (a hidden container hides its descendants), so the client never
 * re-applies permission logic.
 */
function buildTree(items: NavigationItem[]): NavNode[] {
  const map = new Map<string, NavNode>();
  for (const item of items) {
    if (!item.visible) continue;
    map.set(item.slug, { ...item, children: [] });
  }

  const roots: NavNode[] = [];
  for (const node of map.values()) {
    const parent = node.parentSlug ? map.get(node.parentSlug) : undefined;
    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  const byPosition = (a: NavNode, b: NavNode) => (a.position ?? 0) - (b.position ?? 0);
  roots.sort(byPosition);
  for (const node of map.values()) {
    node.children.sort(byPosition);
  }
  return roots;
}

@Component({
  selector: 'app-sidebar-nav',
  imports: [RouterLink, RouterLinkActive, NgTemplateOutlet],
  templateUrl: './sidebar-nav.html',
  styleUrl: './sidebar-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SidebarNavComponent {
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly propCtx = inject(PropertyContextService);

  readonly currentUser = this.authService.currentUser;
  readonly sidebarCollapsed = signal(false);

  /** Slugs of expanded containers (roots + nested groups). */
  readonly openNodes = signal<Set<string>>(new Set());

  /** Navigation tree from the backend, already filtered by permissions. */
  readonly navResource = httpResource<NavigationResponse>(() => '/api/admin/navigation', {
    defaultValue: { items: [] },
  });

  /** Ordered root sections (sistema, gestión, propietario, huésped, …). */
  readonly roots = computed<NavNode[]>(() => buildTree(this.navResource.value()?.items ?? []));

  /** Query params that preserve the current prop_id for hotel-scoped management links. */
  getLinkParams(href: string): Params {
    const pid = this.propCtx.currentPropId();
    if (!pid) return {};
    if (!href.startsWith('/management')) return {};
    if (isGlobalManagementPath(href)) return {};
    return { prop_id: pid };
  }

  constructor() {
    this.authService.ensureSessionLoaded()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();

    // Re-expande cuando el árbol carga (login, F5, deep-link). El constructor
    // corre ANTES de que `httpResource` resuelva, así que sin este efecto el
    // auto-expand nunca se recuperaba y el sidebar quedaba todo colapsado.
    effect(() => {
      const roots = this.roots();
      if (roots.length === 0) return;
      this._autoExpandActiveSection();
    });

    // Auto-expande los ancestros de la ruta activa en cada navegación SPA.
    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => this._autoExpandActiveSection());
  }

  isOpen(slug: string): boolean {
    return this.openNodes().has(slug);
  }

  toggle(slug: string): void {
    this.openNodes.update(prev => {
      const next = new Set(prev);
      if (next.has(slug)) {
        next.delete(slug);
      } else {
        next.add(slug);
      }
      return next;
    });
  }

  /**
   * Expande todos los containers del camino activo sin cerrar lo que el
   * usuario ya abrió a mano (merge, no replace). Incluye el nodo matcheado
   * cuando es container para que sus sub-items sigan visibles.
   */
  private _autoExpandActiveSection(): void {
    const url = this.router.url.split('?')[0];
    const path = this._findPath(this.roots(), url);
    if (!path || path.length < 2) return;

    this.openNodes.update(prev => {
      const next = new Set(prev);
      for (const node of path) {
        if (node.nodeType === 'container') next.add(node.slug);
      }
      return next;
    });
  }

  /**
   * Encuentra el camino al nodo cuyo href matchea la URL con MAYOR
   * especificidad (href más largo), no el primer prefix-match del DFS.
   *
   * Importante: ``gestion.pms`` tiene href ``/management`` (prefijo de toda
   * ruta ``/management/*``). Un primer-match lo elegiría antes que, por
   * ejemplo, ``gestion.reservas`` (``/management/reservations``).
   */
  private _findPath(nodes: NavNode[], url: string): NavNode[] | null {
    let bestPath: NavNode[] | null = null;
    let bestHrefLen = -1;

    const walk = (list: NavNode[], trail: NavNode[]): void => {
      for (const node of list) {
        const path = [...trail, node];
        if (node.href && this._urlCovers(url, node) && node.href.length > bestHrefLen) {
          bestHrefLen = node.href.length;
          bestPath = path;
        }
        walk(node.children, path);
      }
    };
    walk(nodes, []);
    return bestPath;
  }

  /**
   * ¿La URL navegada corresponde realmente a un nodo del árbol?
   * - Exacta → siempre (página del árbol).
   * - Con prefijo → solo si el resto arranca con un ID dinámico (detalle de
   *   entidad, p.ej. ``/management/reservations/BK-123``) o si un descendiente
   *   del nodo cubre ese segmento. Así una página global FUERA del árbol
   *   (p.ej. ``/management/settings`` — Preferencias de cuenta) no expande
   *   el sidebar por el simple prefijo ``/management`` de ``gestion.pms``.
   */
  private _urlCovers(url: string, node: NavNode): boolean {
    const href = node.href ?? '';
    if (url === href) return true;
    if (!href || !url.startsWith(href + '/')) return false;
    const firstSegment = url.slice(href.length + 1).split('/')[0];
    if (DYNAMIC_ID_PATTERN.test(firstSegment)) return true;
    const base = `${href}/${firstSegment}`;
    return this._descendantCovers(node, base);
  }

  /** ¿Algún descendiente tiene href bajo ``prefix`` (o igual)? */
  private _descendantCovers(node: NavNode, prefix: string): boolean {
    const stack = [...node.children];
    while (stack.length > 0) {
      const child = stack.pop()!;
      if (child.href && (child.href === prefix || child.href.startsWith(prefix + '/'))) {
        return true;
      }
      stack.push(...child.children);
    }
    return false;
  }

  /** Destino del link de un container ``horizontal_menu``: su primer hijo.
   *  El grupo no lleva ``href`` propio para no duplicar el href de su hoja. */
  firstChildHref(node: NavNode): string | null {
    return node.children[0]?.href ?? null;
  }

  trackBySlug(_index: number, node: NavNode): string {
    return node.slug;
  }
}
