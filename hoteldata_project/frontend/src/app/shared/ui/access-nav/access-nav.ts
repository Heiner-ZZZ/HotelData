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
  allowedRoles?: string[];
}

interface NavMenuGroup {
  id: string;
  label: string;
  allowedRoles?: string[];
  items: NavMenuItem[];
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

  readonly navigationMenus: NavMenuGroup[] = [
    {
      id: 'explorar',
      label: 'Explorar',
      items: [
        { label: 'Buscar hoteles', href: '/search' },
        { label: 'Hotel destacado', href: '/hotels/partner-1' },
        { label: 'Reservas del viajero', href: '/account/bookings', allowedRoles: ['cliente'] }
      ]
    },
    {
      id: 'cuenta',
      label: 'Cuenta',
      allowedRoles: ['cliente'],
      items: [
        { label: 'Mis reservas', href: '/account/bookings' },
        { label: 'Nuevo viaje', href: '/account/bookings/new' },
        { label: 'Perfil', href: '/account/profile' }
      ]
    },
    {
      id: 'gestion',
      label: 'Gestión',
      allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero'],
      items: [
        { label: 'Panel hotelero', href: '/management' },
        { label: 'Reservas', href: '/management/reservations' },
        { label: 'Propiedades', href: '/management/properties' },
        { label: 'Tarifas', href: '/management/rates' }
      ]
    },
    {
      id: 'sistema',
      label: 'Sistema',
      allowedRoles: ['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'],
      items: [
        { label: 'Usuarios', href: '/system/users' },
        { label: 'Permisos', href: '/system/permissions' },
        { label: 'Auditoría', href: '/system/audit' },
        { label: 'Monitoreo', href: '/system/monitoring' }
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
  }

  toggleMenu(menuId: string, event: MouseEvent) {
    event.stopPropagation();
    this.activeMenu.update((value) => (value === menuId ? null : menuId));
  }

  closeMenus() {
    this.activeMenu.set(null);
  }

  navigateBack() {
    if (window.history.length > 1) {
      this.location.back();
      return;
    }
    void this.router.navigateByUrl(this.authState().homeHref || '/search');
  }

  @HostListener('document:click')
  onDocumentClick() {
    this.closeMenus();
  }
}
