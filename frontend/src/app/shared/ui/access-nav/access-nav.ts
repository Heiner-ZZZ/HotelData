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
  inject,
  signal
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { roleLabel } from '../../../core/auth/role-labels';
import { ThemeService } from '../../../core/theme/theme.service';

interface NavMenuItem {
  label: string;
  href: string;
  icon: string;
  allowedRoles?: string[];
}

interface NavSubGroup {
  label: string;
  icon: string;
  allowedRoles?: string[];
  items: NavMenuItem[];
}

interface NavMenuGroup {
  id: string;
  label: string;
  icon: string;
  allowedRoles?: string[];
  items: (NavMenuItem | NavSubGroup)[];
}

interface SessionMenuItem {
  label: string;
  href: string;
  icon: string;
}

function isSubGroup(item: NavMenuItem | NavSubGroup): item is NavSubGroup {
  return 'items' in item;
}

@Component({
  selector: 'app-access-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './access-nav.html',
  styleUrl: './access-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AccessNavComponent implements AfterViewInit {
  private readonly authService = inject(AuthService);
  private readonly themeService = inject(ThemeService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly location = inject(Location);
  private readonly zone = inject(NgZone);
  private readonly hostElement = inject<ElementRef<HTMLElement>>(ElementRef);
  private removePointerListener: (() => void) | null = null;
  private removePointerLeaveListener: (() => void) | null = null;

  readonly theme = this.themeService;
  readonly authState = this.authService.authState;
  readonly currentUser = this.authService.currentUser;
  readonly roleLabel = roleLabel;
  readonly activeMenu = signal<string | null>(null);
  readonly activeSubMenu = signal<string | null>(null);
  readonly navTransform = signal('translateY(0%)');
  readonly navOpacity = signal(1);
  private readonly SCROLL_HIDE_RANGE = 120;
  private hoverCloseTimer: ReturnType<typeof setTimeout> | null = null;

  readonly isSubGroup = isSubGroup;

  itemHref(item: NavMenuItem | NavSubGroup): string {
    return isSubGroup(item) ? '' : item.href;
  }

  itemIcon(item: NavMenuItem | NavSubGroup): string {
    return isSubGroup(item) ? item.icon : item.icon;
  }

  itemLabel(item: NavMenuItem | NavSubGroup): string {
    return isSubGroup(item) ? item.label : item.label;
  }

  readonly sessionMenuItems = computed<SessionMenuItem[]>(() => {
    const role = this.currentUser()?.primaryRole;
    const homeHref = this.authState().homeHref || '/search';

    if (!role) {
      return [];
    }

    const items: SessionMenuItem[] = [{ label: 'Mi inicio', href: homeHref, icon: 'home' }];

    if (role === 'super_admin') {
      items.push({ label: 'Propietario', href: '/ownership/users', icon: 'assignment_ind' });
    }

    if (['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'].includes(role)) {
      items.push({ label: 'Sistema', href: '/system/users', icon: 'admin_panel_settings' });
    }

    if (['hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'operador_datos', 'auditor_datos', 'recepcionista', 'housekeeping', 'concierge'].includes(role)) {
      items.push({ label: 'Gestión', href: '/management/informes-estrategicos/h01', icon: 'dashboard' });
    }

    if (role === 'cliente') {
      items.push(
        { label: 'Mis reservas', href: '/account/bookings', icon: 'book_online' },
        { label: 'Perfil', href: '/account/profile', icon: 'person' }
      );
    }

    if (role !== 'cliente') {
      const canAccessManagement = ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'operador_datos', 'auditor_datos', 'recepcionista', 'housekeeping', 'concierge'].includes(role);
      if (canAccessManagement) {
        items.push({ label: 'Perfil', href: '/management/profile', icon: 'person' });
      }
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
      id: 'gestion',
      label: 'Gestión',
      icon: 'dashboard',
      allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'operador_datos', 'auditor_datos', 'recepcionista', 'housekeeping', 'concierge'],
      items: [
        { label: 'Panel hotelero', href: '/management/informes-estrategicos/h01', icon: 'dashboard', exact: true } as NavMenuItem,
        {
          label: 'Operación',
          icon: 'assignment',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'recepcionista', 'concierge'],
          items: [
            { label: 'Recepción', href: '/management/recepcion', icon: 'calendar_month' },
            { label: 'Disponibilidad', href: '/management/availability', icon: 'event_available', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager'] },
            { label: 'Check-ins', href: '/management/check-ins', icon: 'login', allowedRoles: ['super_admin', 'admin_sistema', 'gerente_hotel', 'recepcionista', 'concierge'] },
            { label: 'Check-outs', href: '/management/check-outs', icon: 'logout', allowedRoles: ['super_admin', 'admin_sistema', 'gerente_hotel', 'recepcionista', 'concierge'] }
          ]
        } as NavSubGroup,
        {
          label: 'Propiedad',
          icon: 'domain',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero'],
          items: [
            { label: 'Propiedades', href: '/management/properties', icon: 'business', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'revenue_manager', 'marketing_hotelero'] },
            { label: 'Habitaciones', href: '/management/rooms', icon: 'meeting_room', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'] },
            { label: 'Tarifas', href: '/management/rates', icon: 'attach_money', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'revenue_manager'] },
            { label: 'Políticas', href: '/management/policies', icon: 'policy', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'marketing_hotelero'] },
            { label: 'Amenities', href: '/management/amenities', icon: 'spa', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'marketing_hotelero'] }
          ]
        } as NavSubGroup,
        { label: 'Reportes', href: '/management/reports', icon: 'bar_chart', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'auditor_datos', 'operador_datos'] } as NavMenuItem,
        { label: 'Configuración', href: '/management/settings', icon: 'tune', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner'] } as NavMenuItem
      ]
    },
    {
      id: 'propietario',
      label: 'Propietario',
      icon: 'assignment_ind',
      allowedRoles: ['super_admin'],
      items: [
        { label: 'Asignación de hoteles', href: '/ownership/users', icon: 'domain_verification' }
      ]
    },
    {
      id: 'sistema',
      label: 'Sistema',
      icon: 'admin_panel_settings',
      allowedRoles: ['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'],
      items: [
        { label: 'Usuarios', href: '/system/users', icon: 'people', allowedRoles: ['super_admin', 'admin_sistema'] },
        { label: 'Permisos', href: '/system/permissions', icon: 'verified_user', allowedRoles: ['super_admin', 'admin_sistema'] },
        { label: 'Auditoría', href: '/system/audit', icon: 'history' },
        { label: 'Monitoreo', href: '/system/monitoring', icon: 'monitoring' },
        { label: 'Notificaciones', href: '/system/notifications', icon: 'notifications' },
        { label: 'Ganancias', href: '/admin/earnings', icon: 'payments', allowedRoles: ['super_admin'] },
        { label: 'Config. Global', href: '/admin/global-settings', icon: 'tune', allowedRoles: ['super_admin', 'admin_sistema'] },
        { label: 'Geográfico', href: '/admin/geo-catalog', icon: 'map', allowedRoles: ['super_admin', 'admin_sistema'] }
      ]
    }
  ];

  readonly visibleNavigationMenus = computed(() => {
    const role = this.currentUser()?.primaryRole;
    return this.navigationMenus
      .filter((menu) => !menu.allowedRoles?.length || (!!role && menu.allowedRoles.includes(role)))
      .map((menu) => ({
        ...menu,
        items: menu.items
          .map((item) => {
            if (isSubGroup(item)) {
              return {
                ...item,
                items: item.items.filter((sub) => !sub.allowedRoles?.length || (!!role && sub.allowedRoles.includes(role)))
              };
            }
            return item as NavMenuItem;
          })
          .filter((item) => {
            if (isSubGroup(item)) return item.items.length > 0;
            return !(item as NavMenuItem).allowedRoles?.length || (!!role && (item as NavMenuItem).allowedRoles!.includes(role));
          })
      }))
      .filter((menu) => menu.items.length > 0);
  });

  constructor() {
    this.authService
      .ensureSessionLoaded()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
    // Drop the legacy ``ngOnDestroy`` lifecycle hook — register cleanup
    // inline with ``DestroyRef.onDestroy`` so registration is co-located
    // with the listeners they need to remove.
    this.destroyRef.onDestroy(() => {
      this.removePointerListener?.();
      this.removePointerLeaveListener?.();
      if (this.hoverCloseTimer) {
        clearTimeout(this.hoverCloseTimer);
        this.hoverCloseTimer = null;
      }
    });
  }

  ngAfterViewInit() {
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
          this.activeSubMenu.set(null);
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
    if (this.activeMenu() !== menuId) {
      this.activeSubMenu.set(null);
    }
  }

  openSubMenu(label: string) {
    this.activeSubMenu.set(label);
  }

  closeSubMenu() {
    this.activeSubMenu.set(null);
  }

  closeMenus() {
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
      this.hoverCloseTimer = null;
    }
    this.activeMenu.set(null);
    this.activeSubMenu.set(null);
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
