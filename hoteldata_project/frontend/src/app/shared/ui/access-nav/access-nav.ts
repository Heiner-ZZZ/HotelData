import { Location } from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  HostListener,
  NgZone,
  OnDestroy,
  inject,
  signal
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';

interface NavMenuItem {
  label: string;
  href: string;
  icon: string;
  allowedRoles?: string[];
}

interface NavMenuGroup {
  id: string;
  label: string;
  icon: string;
  allowedRoles?: string[];
  items: NavMenuItem[];
}

interface SessionMenuItem {
  label: string;
  href: string;
  icon: string;
}

@Component({
  selector: 'app-access-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './access-nav.html',
  styleUrl: './access-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AccessNavComponent implements AfterViewInit, OnDestroy {
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly location = inject(Location);
  private readonly zone = inject(NgZone);
  private readonly hostElement = inject<ElementRef<HTMLElement>>(ElementRef);
  private removePointerListener: (() => void) | null = null;
  private removePointerLeaveListener: (() => void) | null = null;

  readonly authState = this.authService.authState;
  readonly currentUser = this.authService.currentUser;
  readonly activeMenu = signal<string | null>(null);
  readonly navTransform = signal('translateY(0%)');
  readonly navOpacity = signal(1);
  private readonly SCROLL_HIDE_RANGE = 120;
  private hoverCloseTimer: ReturnType<typeof setTimeout> | null = null;

  readonly sessionMenuItems = computed<SessionMenuItem[]>(() => {
    const role = this.currentUser()?.primaryRole;
    const homeHref = this.authState().homeHref || '/search';

    if (!role) {
      return [];
    }

    const items: SessionMenuItem[] = [{ label: 'Mi inicio', href: homeHref, icon: 'home' }];

    if (role === 'cliente') {
      items.push(
        { label: 'Mis reservas', href: '/account/bookings', icon: 'book_online' },
        { label: 'Perfil', href: '/account/profile', icon: 'person' }
      );
    }

    if (['hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero'].includes(role)) {
      items.push({ label: 'Gestión hotelera', href: '/management', icon: 'dashboard' });
    }

    if (['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'].includes(role)) {
      items.push({ label: 'Sistema', href: '/system/users', icon: 'admin_panel_settings' });
    }

    if (role !== 'cliente') {
      items.push({ label: 'Vista pública', href: '/search', icon: 'public' });
    }

    return items;
  });

  readonly navigationMenus: NavMenuGroup[] = [
    {
      id: 'explorar',
      label: 'Explorar',
      icon: 'explore',
      items: [
        { label: 'Buscar hoteles', href: '/search', icon: 'search' },
        { label: 'Hotel destacado', href: '/hotels/partner-1', icon: 'star' },
        { label: 'Reservas del viajero', href: '/account/bookings', icon: 'book_online', allowedRoles: ['cliente'] }
      ]
    },
    {
      id: 'cuenta',
      label: 'Cuenta',
      icon: 'account_circle',
      allowedRoles: ['cliente'],
      items: [
        { label: 'Mis reservas', href: '/account/bookings', icon: 'book_online' },
        { label: 'Nuevo viaje', href: '/account/bookings/new', icon: 'add_circle' },
        { label: 'Perfil', href: '/account/profile', icon: 'person' }
      ]
    },
    {
      id: 'gestion',
      label: 'Gestión',
      icon: 'dashboard',
      allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero'],
      items: [
        { label: 'Panel hotelero', href: '/management', icon: 'dashboard' },
        { label: 'Reservas', href: '/management/reservations', icon: 'calendar_month' },
        { label: 'Propiedades', href: '/management/properties', icon: 'business' },
        { label: 'Tarifas', href: '/management/rates', icon: 'attach_money' }
      ]
    },
    {
      id: 'sistema',
      label: 'Sistema',
      icon: 'admin_panel_settings',
      allowedRoles: ['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'],
      items: [
        { label: 'Usuarios', href: '/system/users', icon: 'people' },
        { label: 'Permisos', href: '/system/permissions', icon: 'verified_user' },
        { label: 'Auditoría', href: '/system/audit', icon: 'history' },
        { label: 'Monitoreo', href: '/system/monitoring', icon: 'monitoring' }
      ]
    }
  ];

  readonly visibleNavigationMenus = computed(() => {
    const role = this.currentUser()?.primaryRole;
    return this.navigationMenus
      .filter((menu) => !menu.allowedRoles?.length || (!!role && menu.allowedRoles.includes(role)))
      .map((menu) => ({
        ...menu,
        items: menu.items.filter((item) => !item.allowedRoles?.length || (!!role && item.allowedRoles.includes(role)))
      }))
      .filter((menu) => menu.items.length > 0);
  });

  constructor() {
    this.authService
      .ensureSessionLoaded()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  ngAfterViewInit() {
    // Init nav position based on current scroll position
    const scrollY = window.scrollY;
    const initProgress = Math.min(scrollY / this.SCROLL_HIDE_RANGE, 1);
    this.navTransform.set(`translateY(${(initProgress * -120).toFixed(1)}%)`);
    this.navOpacity.set(1 - initProgress);

    const element = this.hostElement.nativeElement;

    this.zone.runOutsideAngular(() => {
      const onPointerMove = (event: PointerEvent) => {
        const rect = element.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * 100;
        const y = ((event.clientY - rect.top) / rect.height) * 100;
        element.style.setProperty('--pointer-x', `${x.toFixed(2)}%`);
        element.style.setProperty('--pointer-y', `${y.toFixed(2)}%`);
      };

      const onPointerLeave = () => {
        element.style.setProperty('--pointer-x', '82%');
        element.style.setProperty('--pointer-y', '24%');
      };

      element.addEventListener('pointermove', onPointerMove, { passive: true });
      element.addEventListener('pointerleave', onPointerLeave, { passive: true });

      this.removePointerListener = () => element.removeEventListener('pointermove', onPointerMove);
      this.removePointerLeaveListener = () => element.removeEventListener('pointerleave', onPointerLeave);
    });
  }

  ngOnDestroy() {
    this.removePointerListener?.();
    this.removePointerLeaveListener?.();
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
      this.hoverCloseTimer = null;
    }
  }

  onMenuEnter(menuId: string) {
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
      this.hoverCloseTimer = null;
    }
    this.activeMenu.set(menuId);
  }

  onMenuLeave(menuId: string) {
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
    }
    this.hoverCloseTimer = setTimeout(() => {
      this.zone.run(() => {
        if (this.activeMenu() === menuId) {
          this.activeMenu.set(null);
        }
      });
    }, 200);
  }

  toggleMenu(menuId: string, event: MouseEvent) {
    event.stopPropagation();
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
      this.hoverCloseTimer = null;
    }
    this.activeMenu.update((value) => (value === menuId ? null : menuId));
  }

  closeMenus() {
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
      this.hoverCloseTimer = null;
    }
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
    const translateY = progress * -120;
    const opacity = 1 - progress;

    this.zone.run(() => {
      this.navTransform.set(`translateY(${translateY.toFixed(1)}%)`);
      this.navOpacity.set(opacity);
    });
  }

  @HostListener('document:click')
  onDocumentClick() {
    this.closeMenus();
  }
}
