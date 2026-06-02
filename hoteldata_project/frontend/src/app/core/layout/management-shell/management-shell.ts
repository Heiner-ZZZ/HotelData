import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AccessNavComponent } from '../../../shared/ui/access-nav/access-nav';

interface ManagementNavGroup {
  label: string;
  items: Array<{ label: string; href: string; exact?: boolean }>;
}

@Component({
  selector: 'app-management-shell',
  imports: [AccessNavComponent, RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './management-shell.html',
  styleUrl: './management-shell.scss'
})
export class ManagementShellComponent {
  readonly navigation: ManagementNavGroup[] = [
    {
      label: 'Dashboard',
      items: [{ label: 'Resumen', href: '/management', exact: true }]
    },
    {
      label: 'Operacion',
      items: [
        { label: 'Reservas', href: '/management/reservations' },
        { label: 'Disponibilidad', href: '/management/availability' },
        { label: 'Check-ins', href: '/management/check-ins' },
        { label: 'Check-outs', href: '/management/check-outs' }
      ]
    },
    {
      label: 'Propiedad',
      items: [
        { label: 'Propiedades', href: '/management/properties' },
        { label: 'Habitaciones', href: '/management/rooms' },
        { label: 'Tarifas', href: '/management/rates' },
        { label: 'Politicas', href: '/management/policies' },
        { label: 'Amenities', href: '/management/amenities' }
      ]
    },
    {
      label: 'Reportes',
      items: [{ label: 'Reportes', href: '/management/reports' }]
    },
    {
      label: 'Configuracion',
      items: [{ label: 'Ajustes', href: '/management/settings' }]
    }
  ];
}
