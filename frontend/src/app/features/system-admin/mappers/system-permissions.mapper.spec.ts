import { mapNavigationItem } from './system-permissions.mapper';

describe('mapNavigationItem (wire → model)', () => {
  it('maps the tree node fields (slug/parentSlug/position/nodeType) into the model', () => {
    const item = mapNavigationItem({
      slug: 'gestion.reservas.informes.adr',
      parentSlug: 'gestion.reservas.informes',
      position: 10,
      nodeType: 'leaf',
      label: 'Dashboard ADR',
      href: '/management/rates/dashboard',
      icon: 'monitoring',
      visible: true,
      permissionId: 'abc123',
      permissionCode: 'reports.rates.adr.read',
    });

    expect(item.slug).toBe('gestion.reservas.informes.adr');
    expect(item.parentSlug).toBe('gestion.reservas.informes');
    expect(item.position).toBe(10);
    expect(item.nodeType).toBe('leaf');
    expect(item.label).toBe('Dashboard ADR');
    expect(item.href).toBe('/management/rates/dashboard');
    expect(item.permissionCode).toBe('reports.rates.adr.read');
    expect(item.permissionId).toBe('abc123');
  });

  it('maps containers (empty href) and translates legacy icon names', () => {
    const item = mapNavigationItem({
      slug: 'gestion.reservas.informes',
      parentSlug: 'gestion.reservas',
      position: 30,
      nodeType: 'container',
      label: 'Informes',
      href: '',
      icon: 'icon-analytics',
      visible: true,
      permissionCode: 'reports.tactical.read',
    });

    expect(item.nodeType).toBe('container');
    expect(item.href).toBe('');
    expect(item.icon).toBe('analytics');
    expect(item.permissionCode).toBe('reports.tactical.read');
  });

  it('defaults permissionId/permissionCode to null when absent', () => {
    const item = mapNavigationItem({
      slug: 'gestion',
      parentSlug: null,
      position: 10,
      nodeType: 'container',
      label: 'Gestión',
      href: '',
      icon: 'dashboard',
      visible: true,
    });

    expect(item.parentSlug).toBeNull();
    expect(item.permissionId).toBeNull();
    expect(item.permissionCode).toBeNull();
  });
});
