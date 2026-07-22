import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { httpResource } from '@angular/common/http';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { filter } from 'rxjs';
import type { Params } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { ThemeService } from '../../../core/theme/theme.service';
import { PropertyContextService } from '../../../shared/services/property-context.service';

interface SidebarItem {
  label: string;
  href: string;
  icon: string;
  visible: boolean;
  section?: string | null;
  is_section_header?: boolean;
}

interface SidebarSubSection {
  id: string;
  label: string;
  icon: string;
  href?: string;
  items: SidebarItem[];
}

interface SidebarSection {
  id: string;
  label: string;
  icon: string;
  items: SidebarItem[];
  subSections: SidebarSubSection[];
}

interface NavigationResponse {
  items: SidebarItem[];
}

@Component({
  selector: 'app-sidebar-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './sidebar-nav.html',
  styleUrl: './sidebar-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SidebarNavComponent {
  private readonly authService = inject(AuthService);
  private readonly themeService = inject(ThemeService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly propCtx = inject(PropertyContextService);

  readonly theme = this.themeService;
  readonly currentUser = this.authService.currentUser;
  readonly sidebarCollapsed = signal(false);
  readonly openSection = signal<string | null>(null);

  /** Query params that preserve the current prop_id for management links. */
  readonly linkParams = computed<Params>(() => {
    const pid = this.propCtx.currentPropId();
    return pid ? { prop_id: pid } : {};
  });

  /** Navigation items from the backend, filtered by user permissions. */
  readonly navResource = httpResource<NavigationResponse>(() => '/api/admin/navigation', {
    defaultValue: { items: [] },
  });

  /** Open sub-section IDs within each main section. key: "sectionId:subSectionId" */
  readonly openSubSection = signal<string | null>(null);

  /** Group navigation items into collapsible sections by href prefix,
   *  with nested sub-sections for items that share a ``section`` field. */
  readonly sections = computed<SidebarSection[]>(() => {
    const items = this.navResource.value()?.items ?? [];
    const visible = items.filter(i => i.visible);

    // Define section grouping rules: id, label, icon, href prefix matcher
    const sectionDefs = [
      { id: 'sistema', label: 'Sistema', icon: 'admin_panel_settings', prefix: '/system/' },
      { id: 'sistema', label: 'Sistema', icon: 'admin_panel_settings', prefix: '/admin/' },
      { id: 'propietario', label: 'Propietario', icon: 'assignment_ind', prefix: '/ownership/' },
      { id: 'gestion', label: 'Gestión', icon: 'dashboard', prefix: '/management/' },
      { id: 'huesped', label: 'Huésped', icon: 'person', prefix: '/search' },
      { id: 'huesped', label: 'Huésped', icon: 'person', prefix: '/account/' },
    ];

    const sectionMap = new Map<string, SidebarItem[]>();
    const sectionMeta = new Map<string, { label: string; icon: string }>();

    for (const def of sectionDefs) {
      if (!sectionMap.has(def.id)) {
        sectionMap.set(def.id, []);
        sectionMeta.set(def.id, { label: def.label, icon: def.icon });
      }
    }

    for (const item of visible) {
      for (const def of sectionDefs) {
        if (this._hrefInSection(item.href, def.prefix)) {
          sectionMap.get(def.id)!.push(item);
          break;
        }
      }
    }

    // Build ordered sections with sub-section grouping
    const orderedIds = ['gestion', 'sistema', 'propietario', 'huesped'];
    return orderedIds
      .filter(id => sectionMap.has(id) && sectionMap.get(id)!.length > 0)
      .map(id => {
        const rawItems = sectionMap.get(id)!;
        return this._groupIntoSubSections(id, rawItems, sectionMeta.get(id)!);
      });
  });

  /** Split items into flat links and sub-section groups. */
  private _groupIntoSubSections(
    parentId: string,
    items: SidebarItem[],
    meta: { label: string; icon: string },
  ): SidebarSection {
    const flatItems: SidebarItem[] = [];
    const subGroups = new Map<string, { header: SidebarItem | null; children: SidebarItem[] }>();

    for (const item of items) {
      const section = item.section || null;
      if (!section) {
        flatItems.push(item);
        continue;
      }

      if (!subGroups.has(section)) {
        subGroups.set(section, { header: null, children: [] });
      }
      const group = subGroups.get(section)!;

      if (item.is_section_header) {
        group.header = item;
      } else {
        group.children.push(item);
      }
    }

    const subSections: SidebarSubSection[] = [];
    for (const [sectionName, group] of subGroups) {
      if (group.children.length === 0) continue;
      subSections.push({
        id: `${parentId}:${sectionName}`,
        label: group.header?.label ?? sectionName,
        icon: group.header?.icon ?? 'folder',
        href: group.header?.href,
        items: group.children,
      });
    }

    return {
      id: parentId,
      label: meta.label,
      icon: meta.icon,
      items: flatItems,
      subSections,
    };
  }

  readonly visibleSections = this.sections;

  constructor() {
    this.authService.ensureSessionLoaded()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();

    // Auto-expand the section containing the current route on navigation
    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => this._autoExpandActiveSection());

    // Expand on first load
    this._autoExpandActiveSection();
  }

  private _autoExpandActiveSection(): void {
    const url = this.router.url.split('?')[0];
    for (const section of this.visibleSections()) {
      // Check flat items
      for (const item of section.items) {
        if (this._urlMatches(url, item.href)) {
          this.openSection.set(section.id);
          return;
        }
      }
      // Check sub-section items
      for (const sub of section.subSections) {
        for (const item of sub.items) {
          if (this._urlMatches(url, item.href)) {
            this.openSection.set(section.id);
            this.openSubSection.set(sub.id);
            return;
          }
        }
      }
    }
  }

  private _urlMatches(current: string, target: string): boolean {
    return current === target || current.startsWith(target + '/');
  }

  toggleSection(id: string) {
    this.openSection.update(v => v === id ? null : id);
  }

  toggleSubSection(id: string) {
    this.openSubSection.update(v => v === id ? null : id);
  }

  /** Match an href against a section prefix. If prefix ends with ``/``,
   *  also match the exact href without the trailing slash (e.g. ``/management`` vs ``/management/``). */
  private _hrefInSection(href: string, prefix: string): boolean {
    if (href.startsWith(prefix)) return true;
    if (prefix.endsWith('/') && href === prefix.slice(0, -1)) return true;
    return false;
  }

  trackByHref(_index: number, item: SidebarItem): string {
    return item.href;
  }
}
