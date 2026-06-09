import { Location } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  HostListener,
  inject,
  signal
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { ThemeService } from '../../../core/theme/theme.service';

interface TopNavItem {
  label: string;
  href: string;
  icon: string;
  allowedRoles?: string[];
}

interface TopNavGroup {
  id: string;
  label: string;
  icon: string;
  allowedRoles?: string[];
  items: TopNavItem[];
}

@Component({
  selector: 'app-top-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './top-nav.html',
  styleUrl: './top-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TopNavComponent {
  private readonly authService = inject(AuthService);
  private readonly themeService = inject(ThemeService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly location = inject(Location);

  readonly theme = this.themeService;
  readonly authState = this.authService.authState;
  readonly currentUser = this.authService.currentUser;
  readonly activeMenu = signal<string | null>(null);
  readonly navTransform = signal('translateY(0%)');
  readonly navOpacity = signal(1);
  private readonly SCROLL_HIDE_RANGE = 120;
  private hoverCloseTimer: ReturnType<typeof setTimeout> | null = null;

  readonly sessionMenuItems = computed(() => {
    const role = this.currentUser()?.primaryRole;
    const homeHref = this.authState().homeHref || '/search';
    if (!role) return [];
    const items: { label: string; href: string; icon: string }[] = [
      { label: 'Mi inicio', href: homeHref, icon: 'home' }
    ];
    if (['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'].includes(role)) {
      items.push({ label: 'Sistema', href: '/system/users', icon: 'admin_panel_settings' });
    }
    if (['hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'operador_datos', 'auditor_datos'].includes(role)) {
      items.push({ label: 'Gestión', href: '/management', icon: 'dashboard' });
    }
    if (role === 'cliente') {
      items.push(
        { label: 'Mis reservas', href: '/account/bookings', icon: 'book_online' },
        { label: 'Perfil', href: '/account/profile', icon: 'person' }
      );
    }
    if (role !== 'cliente') {
      items.push({ label: 'Vista pública', href: '/search', icon: 'public' });
    }
    return items;
  });

  readonly navGroups: TopNavGroup[] = [
    {
      id: 'explorar',
      label: 'Explorar',
      icon: 'explore',
      items: [
        { label: 'Buscar hoteles', href: '/search', icon: 'search' },
        { label: 'Hotel destacado', href: '/hotels/partner-1', icon: 'star' },
        { label: 'Reservas del viajero', href: '/account/bookings', icon: 'book_online', allowedRoles: ['cliente'] }
      ]
    }
  ];

  readonly visibleGroups = computed(() => {
    const role = this.currentUser()?.primaryRole;
    return this.navGroups
      .map(g => ({
        ...g,
        items: g.items.filter(i => !i.allowedRoles?.length || (!!role && i.allowedRoles.includes(role)))
      }))
      .filter(g => g.items.length > 0);
  });

  constructor() {
    this.authService.ensureSessionLoaded()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  onMenuEnter(id: string) {
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
      this.hoverCloseTimer = null;
    }
    this.activeMenu.set(id);
  }

  onMenuLeave(id: string) {
    if (this.hoverCloseTimer) clearTimeout(this.hoverCloseTimer);
    this.hoverCloseTimer = setTimeout(() => {
      if (this.activeMenu() === id) {
        this.activeMenu.set(null);
      }
    }, 200);
  }

  toggleMenu(id: string, event: MouseEvent) {
    event.stopPropagation();
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
      this.hoverCloseTimer = null;
    }
    this.activeMenu.update(v => v === id ? null : id);
  }

  closeMenus() {
    if (this.hoverCloseTimer) clearTimeout(this.hoverCloseTimer);
    this.activeMenu.set(null);
  }

  navigateBack() {
    if (window.history.length > 1) {
      this.location.back();
      return;
    }
    void this.router.navigateByUrl(this.authState().homeHref || '/search');
  }

  @HostListener('window:scroll')
  onWindowScroll() {
    const scrollY = window.scrollY;
    const progress = Math.min(scrollY / this.SCROLL_HIDE_RANGE, 1);
    this.navTransform.set(`translateY(${(progress * -120).toFixed(1)}%)`);
    this.navOpacity.set(1 - progress);
  }

  @HostListener('document:click')
  onDocClick() {
    this.closeMenus();
  }
}
