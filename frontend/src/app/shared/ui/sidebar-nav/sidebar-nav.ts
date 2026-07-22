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
}

interface SidebarSection {
  id: string;
  label: string;
  icon: string;
  items: SidebarItem[];
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

  /** Group navigation items into collapsible sections by href prefix. */
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
        if (item.href.startsWith(def.prefix)) {
          sectionMap.get(def.id)!.push(item);
          break;
        }
      }
    }

    // Build ordered sections (only include those with items)
    const orderedIds = ['gestion', 'sistema', 'propietario', 'huesped'];
    return orderedIds
      .filter(id => sectionMap.has(id) && sectionMap.get(id)!.length > 0)
      .map(id => ({
        id,
        label: sectionMeta.get(id)!.label,
        icon: sectionMeta.get(id)!.icon,
        items: sectionMap.get(id)!,
      }));
  });

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
      for (const item of section.items) {
        if (url === item.href || url.startsWith(item.href + '/')) {
          this.openSection.set(section.id);
          return;
        }
      }
    }
  }

  toggleSection(id: string) {
    this.openSection.update(v => v === id ? null : id);
  }

  trackByHref(_index: number, item: SidebarItem): string {
    return item.href;
  }
}
