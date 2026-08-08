import { mapNavigationItem } from './system-permissions.mapper';

describe('mapNavigationItem (wire → model)', () => {
  it('maps requiredPermission (camelCase as emitted by the server) into the model', () => {
    const item = mapNavigationItem({
      label: 'Reservas',
      href: '/management/reservations',
      icon: 'icon-booking',
      visible: true,
      section: 'CRS',
      is_section_header: true,
      requiredPermission: 'reservations.read',
      permissionId: 'abc123',
    });

    expect(item.requiredPermission).toBe('reservations.read');
    expect(item.section).toBe('CRS');
    expect(item.isSectionHeader).toBe(true);
    expect(item.permissionId).toBe('abc123');
  });

  it('falls back to required_permission (snake_case) defensively', () => {
    const item = mapNavigationItem({
      label: 'Tarifas',
      href: '/management/rates',
      icon: 'icon-revenue',
      visible: true,
      required_permission: 'rates.read',
    });

    expect(item.requiredPermission).toBe('rates.read');
  });

  it('defaults requiredPermission to null when absent', () => {
    const item = mapNavigationItem({
      label: 'Dashboard',
      href: '/management',
      icon: 'icon-dashboard',
      visible: true,
    });

    expect(item.requiredPermission).toBeNull();
  });
});
