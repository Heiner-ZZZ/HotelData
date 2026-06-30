import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

interface NavItem {
  label: string;
  href: string;
  icon: string;
}

@Component({
  selector: 'app-housekeeping-sub-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './housekeeping-sub-nav.html',
  styleUrl: './housekeeping-sub-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HousekeepingSubNavComponent {
  readonly navItems: NavItem[] = [
    { label: 'Dashboard', href: '/management/housekeeping/dashboard', icon: 'dashboard' },
    { label: 'Calendario', href: '/management/housekeeping/calendar', icon: 'calendar_month' },
    { label: 'Habitaciones', href: '/management/housekeeping/rooms', icon: 'meeting_room' },
    { label: 'Tareas', href: '/management/housekeeping/tasks', icon: 'checklist' },
    { label: 'Mantenimiento', href: '/management/housekeeping/maintenance', icon: 'build' },
    { label: 'Cargos', href: '/management/housekeeping/charges', icon: 'receipt_long' },
    { label: 'Historial', href: '/management/housekeeping/history', icon: 'history' },
  ];
}
