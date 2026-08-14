import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { RouterLink, RouterLinkActive } from '@angular/router';

/** Flat wire node from ``GET /api/admin/navigation`` (same contract as sidebar-nav). */
interface NavigationItem {
  slug: string;
  parentSlug: string | null;
  position: number;
  nodeType: string | null;
  label: string;
  href: string | null;
  icon: string;
  visible: boolean;
  permissionCode: string | null;
}

interface NavigationResponse {
  items: NavigationItem[];
}

interface NavLink {
  label: string;
  href: string;
  icon: string;
}

/**
 * Horizontal sub-navigation for a group of reports (dashboards tácticos).
 *
 * Fed by the SAME backend navigation tree as the sidebar: given a node slug,
 * it renders the visible sibling leaves of that node as a horizontal bar.
 * Passing a leaf slug resolves to its parent container; passing a container
 * slug lists that container's children directly.
 */
@Component({
  selector: 'app-horizontal-sub-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './horizontal-sub-nav.html',
  styleUrl: './horizontal-sub-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HorizontalSubNavComponent {
  /** Slug of the active node (leaf report or its parent container). */
  readonly activeSlug = input<string>('');

  readonly navResource = httpResource<NavigationResponse>(() => '/api/admin/navigation', {
    defaultValue: { items: [] },
  });

  /** Visible, navigable siblings to render as the horizontal bar. */
  readonly items = computed<NavLink[]>(() => {
    const all = this.navResource.value()?.items ?? [];
    const active = all.find(i => i.slug === this.activeSlug());
    if (!active) return [];

    // A leaf belongs to its parent's group; a container IS the group.
    const groupSlug = active.nodeType === 'leaf' ? active.parentSlug : active.slug;
    if (!groupSlug) return [];

    return all
      .filter(i => i.parentSlug === groupSlug && i.visible && i.nodeType === 'leaf' && i.href)
      .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
      .map(i => ({ label: i.label, href: i.href as string, icon: i.icon }));
  });

  trackByHref(_index: number, item: NavLink): string {
    return item.href;
  }
}
