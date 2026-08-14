import {
  computeNavVisibility,
  countSectionCodes,
  countSectionCodesWithHidden,
  expandManageCodes,
  filterResourcesByQuery,
  isMatrixVisibleCode,
  MATRIX_BASE_ACTIONS,
  MATRIX_CONDITIONAL_ACTIONS,
  matrixActionColumns,
  matrixHiddenCodes,
  sectionForNavItem,
  sectionForResource,
} from './role-permission-sections';

describe('expandManageCodes', () => {
  it('expands resource.manage into CRUD codes', () => {
    const result = expandManageCodes(['users.manage']);
    expect(result).toEqual(
      new Set(['users.manage', 'users.create', 'users.read', 'users.update', 'users.delete']),
    );
  });

  it('keeps compound codes and execute untouched', () => {
    const result = expandManageCodes(['hotel.manage_roles', 'etl.execute', '*.*']);
    expect(result.has('hotel.manage_roles')).toBe(true);
    expect(result.has('etl.execute')).toBe(true);
    expect(result.has('*.*')).toBe(true);
    // compound "manage_roles" must NOT expand to hotel.create/read/update/delete
    expect(result.has('hotel.read')).toBe(false);
  });
});

describe('countSectionCodes', () => {
  const resources = [
    {
      resource: 'reservations',
      actions: {
        manage: { code: 'reservations.manage', description: '' },
        read: { code: 'reservations.read', description: '' },
        create: { code: 'reservations.create', description: '' },
        update: { code: 'reservations.update', description: '' },
        delete: { code: 'reservations.delete', description: '' },
      },
    },
    {
      resource: 'check-ins',
      actions: {
        manage: { code: 'check-ins.manage', description: '' },
        read: { code: 'check-ins.read', description: '' },
      },
    },
  ];

  it('counts total codes across all resources of the section', () => {
    const { total } = countSectionCodes(resources, ['reservations.read']);
    expect(total).toBe(7);
  });

  it('counts selected codes present in the selection', () => {
    const { selected } = countSectionCodes(resources, [
      'reservations.read',
      'reservations.manage',
      'check-ins.manage',
    ]);
    expect(selected).toBe(3);
  });

  it('returns zero when there are no resources or selection', () => {
    expect(countSectionCodes([], [])).toEqual({ selected: 0, total: 0 });
  });

  it('counts every catalog code of the section, never only the manage entries', () => {
    // Regresión del conteo "X/Y": una implementación que solo sumara los
    // permisos `manage` diría total=2; el total real es 6 (3 + 3 códigos).
    const mixed = [
      {
        resource: 'users',
        actions: {
          manage: { code: 'users.manage', description: '' },
          read: { code: 'users.read', description: '' },
          create: { code: 'users.create', description: '' },
        },
      },
      {
        resource: 'etl',
        actions: {
          manage: { code: 'etl.manage', description: '' },
          read: { code: 'etl.read', description: '' },
          execute: { code: 'etl.execute', description: '' },
        },
      },
    ];
    expect(countSectionCodes(mixed, []).total).toBe(6);
    expect(countSectionCodes(mixed, ['users.read', 'etl.execute']).selected).toBe(2);
  });
});

describe('filterResourcesByQuery', () => {
  const resources = [
    {
      resource: 'reservations',
      actions: {
        read: { code: 'reservations.read', description: 'Ver reservas' },
      },
    },
    {
      resource: 'check-ins',
      actions: {
        read: { code: 'check-ins.read', description: 'Ver check-ins' },
      },
    },
  ];

  it('returns everything for an empty or blank query', () => {
    expect(filterResourcesByQuery(resources, '')).toHaveLength(2);
    expect(filterResourcesByQuery(resources, '   ')).toHaveLength(2);
  });

  it('matches by resource name (case-insensitive)', () => {
    const result = filterResourcesByQuery(resources, 'CHECK');
    expect(result.map((r) => r.resource)).toEqual(['check-ins']);
  });

  it('matches by full permission code', () => {
    const result = filterResourcesByQuery(resources, 'reservations.read');
    expect(result.map((r) => r.resource)).toEqual(['reservations']);
  });

  it('matches by description text (not present in name/code)', () => {
    const described = [
      {
        resource: 'reservations',
        actions: {
          read: { code: 'reservations.read', description: 'Ver reservas en el hotel' },
        },
      },
      {
        resource: 'check-ins',
        actions: {
          read: { code: 'check-ins.read', description: 'Ver entradas' },
        },
      },
    ];
    const result = filterResourcesByQuery(described, 'en el hotel');
    expect(result.map((r) => r.resource)).toEqual(['reservations']);
  });

  it('returns empty array when nothing matches', () => {
    expect(filterResourcesByQuery(resources, 'housekeeping')).toHaveLength(0);
  });
});

describe('matrixActionColumns', () => {
  const BASE = ['manage', 'read', 'create', 'update', 'delete', 'execute'] as const;
  const EXTRA = ['moderate'] as const;

  const reviewsWithModerate: Array<{ resource: string; actions: Record<string, { code: string } | undefined> }> = [
    {
      resource: 'reviews',
      actions: {
        read: { code: 'reviews.read' },
        moderate: { code: 'reviews.moderate' },
      },
    },
  ];

  const noModerate: Array<{ resource: string; actions: Record<string, { code: string } | undefined> }> = [
    {
      resource: 'users',
      actions: {
        manage: { code: 'users.manage' },
        read: { code: 'users.read' },
      },
    },
  ];

  it('shows only base CRUD columns when no resource has the extra action', () => {
    expect(matrixActionColumns(noModerate, BASE, EXTRA)).toEqual([...BASE]);
  });

  it('appends the extra column when a resource has that action', () => {
    expect(matrixActionColumns(reviewsWithModerate, BASE, EXTRA)).toEqual([...BASE, 'moderate']);
  });

  it('keeps base column order and appends extras at the end', () => {
    const cols = matrixActionColumns(reviewsWithModerate, BASE, EXTRA);
    expect(cols.slice(0, BASE.length)).toEqual([...BASE]);
    expect(cols.slice(BASE.length)).toEqual(['moderate']);
  });

  it('handles empty resources defensively', () => {
    expect(matrixActionColumns([], BASE, EXTRA)).toEqual([...BASE]);
  });

  it('never emits a column for actions not in extraActions (compounds/multi-dot)', () => {
    const withCompounds: Array<{ resource: string; actions: Record<string, { code: string } | undefined> }> = [
      {
        resource: 'hotel',
        actions: { manage_roles: { code: 'hotel.manage_roles' } },
      },
      {
        resource: 'inventory',
        actions: { 'products.cost.read': { code: 'inventory.products.cost.read' } },
      },
      {
        resource: 'reviews',
        actions: {
          read: { code: 'reviews.read' },
          moderate: { code: 'reviews.moderate' },
        },
      },
    ];
    const cols = matrixActionColumns(withCompounds, BASE, EXTRA);
    expect(cols).not.toContain('manage_roles');
    expect(cols).not.toContain('products.cost.read');
    expect(cols).toContain('moderate');
  });
});

describe('matrix action column configuration (execute/moderate condicionales)', () => {
  const usersOnly = [
    {
      resource: 'users',
      actions: {
        manage: { code: 'users.manage' },
        read: { code: 'users.read' },
      },
    },
  ];
  const withExecute = [
    {
      resource: 'etl',
      actions: {
        manage: { code: 'etl.manage' },
        read: { code: 'etl.read' },
        execute: { code: 'etl.execute' },
      },
    },
  ];
  const withExecuteAndModerate = [
    ...withExecute,
    {
      resource: 'reviews',
      actions: {
        read: { code: 'reviews.read' },
        moderate: { code: 'reviews.moderate' },
      },
    },
  ];

  it('keeps the five CRUD actions always visible', () => {
    const cols = matrixActionColumns(usersOnly, MATRIX_BASE_ACTIONS, MATRIX_CONDITIONAL_ACTIONS);
    expect(MATRIX_BASE_ACTIONS.every((action) => cols.includes(action))).toBe(true);
  });

  it('does NOT draw execute or moderate when no resource has them', () => {
    const cols = matrixActionColumns(usersOnly, MATRIX_BASE_ACTIONS, MATRIX_CONDITIONAL_ACTIONS);
    expect(cols).not.toContain('execute');
    expect(cols).not.toContain('moderate');
  });

  it('draws execute when at least one resource has it', () => {
    const cols = matrixActionColumns(withExecute, MATRIX_BASE_ACTIONS, MATRIX_CONDITIONAL_ACTIONS);
    expect(cols).toContain('execute');
    expect(cols).not.toContain('moderate');
  });

  it('renders the full 7-column matrix only when both are present, in order', () => {
    const cols = matrixActionColumns(withExecuteAndModerate, MATRIX_BASE_ACTIONS, MATRIX_CONDITIONAL_ACTIONS);
    expect(cols).toEqual(['manage', 'read', 'create', 'update', 'delete', 'execute', 'moderate']);
  });
});

describe('matrixHiddenCodes (códigos que la matriz CRUD no dibuja)', () => {
  const KNOWN = [...MATRIX_BASE_ACTIONS, ...MATRIX_CONDITIONAL_ACTIONS];

  it('returns compound/approve codes whose 2nd segment is not a known action', () => {
    const permissions = [
      { code: 'properties.approve', description: 'Aprobar propiedad' },
      { code: 'hotel.manage_roles', description: 'Gestionar roles del equipo' },
      { code: 'inventory.products.cost.read', description: 'Ver costos' },
      { code: 'users.read', description: 'Ver usuarios' },
    ];
    const hidden = matrixHiddenCodes(permissions, KNOWN).map((p) => p.code);
    expect(hidden).toEqual(['properties.approve', 'hotel.manage_roles', 'inventory.products.cost.read']);
  });

  it('returns empty when every code splits into a known action', () => {
    const permissions = [
      { code: 'users.manage', description: '' },
      { code: 'users.read', description: '' },
      { code: 'etl.execute', description: '' },
      { code: 'reviews.moderate', description: '' },
    ];
    expect(matrixHiddenCodes(permissions, KNOWN)).toHaveLength(0);
  });

  it('treats execute/moderate as hidden when they are not in knownActions', () => {
    const permissions = [{ code: 'etl.execute' }, { code: 'reviews.moderate' }];
    const hidden = matrixHiddenCodes(permissions, ['manage', 'read']).map((p) => p.code);
    expect(hidden).toEqual(['etl.execute', 'reviews.moderate']);
  });

  it('treats no-dot codes and wildcards as hidden (cannot render a column)', () => {
    const permissions = [{ code: 'legacy' }, { code: '*.*' }];
    expect(matrixHiddenCodes(permissions, KNOWN)).toHaveLength(2);
  });

  it('keeps the description alongside the code for the chips', () => {
    const hidden = matrixHiddenCodes([{ code: 'properties.approve', description: 'Aprobar propiedad' }], KNOWN);
    expect(hidden[0].description).toBe('Aprobar propiedad');
  });

  it('hides codes with an EMPTY resource even when the action is known (espejo exacto de resourceRows)', () => {
    // resourceRows descarta `!resource || !KNOWN_ACTIONS.has(action)`; lo que
    // no es visible debe ser oculto para que visible+hidden == total del catálogo.
    expect(matrixHiddenCodes([{ code: '.read' }], KNOWN)).toHaveLength(1);
  });
});

describe('isMatrixVisibleCode (predicado compartido con resourceRows)', () => {
  it('requires a non-empty resource AND a known action', () => {
    expect(isMatrixVisibleCode('users.read', MATRIX_BASE_ACTIONS)).toBe(true);
    expect(isMatrixVisibleCode('properties.approve', MATRIX_BASE_ACTIONS)).toBe(false);
    expect(isMatrixVisibleCode('.read', MATRIX_BASE_ACTIONS)).toBe(false);
    expect(isMatrixVisibleCode('users', MATRIX_BASE_ACTIONS)).toBe(false);
  });

  it('treats execute/moderate as visible when listed in knownActions', () => {
    const known = [...MATRIX_BASE_ACTIONS, ...MATRIX_CONDITIONAL_ACTIONS];
    expect(isMatrixVisibleCode('etl.execute', known)).toBe(true);
    expect(isMatrixVisibleCode('reviews.moderate', known)).toBe(true);
  });
});

describe('countSectionCodesWithHidden (matriz + compuestos = total de la sección)', () => {
  const resources = [
    {
      resource: 'reservations',
      actions: {
        read: { code: 'reservations.read' },
        create: { code: 'reservations.create' },
      },
    },
  ];
  const hiddenCodes = [{ code: 'hotel.manage_roles' }, { code: 'properties.approve' }];

  it('sums matrix totals and hidden codes without double counting', () => {
    const { total } = countSectionCodesWithHidden(resources, hiddenCodes, []);
    expect(total).toBe(4);
  });

  it('counts selected across matrix rows and hidden chips', () => {
    const { selected } = countSectionCodesWithHidden(resources, hiddenCodes, [
      'reservations.read',
      'hotel.manage_roles',
    ]);
    expect(selected).toBe(2);
  });

  it('returns zero when everything is empty', () => {
    expect(countSectionCodesWithHidden([], [], [])).toEqual({ selected: 0, total: 0 });
  });
});

describe('sectionForResource', () => {
  it('maps users/roles/audit/etl/settings to Sistema', () => {
    expect(sectionForResource('users')).toBe('Sistema');
    expect(sectionForResource('roles')).toBe('Sistema');
    expect(sectionForResource('etl')).toBe('Sistema');
  });

  it('maps reservations/inventory/rates/check-ins to CRS', () => {
    expect(sectionForResource('reservations')).toBe('CRS');
    expect(sectionForResource('inventory')).toBe('CRS');
    expect(sectionForResource('check-ins')).toBe('CRS');
  });

  it('maps housekeeping/charges/lost-found to Housekeeping', () => {
    expect(sectionForResource('housekeeping')).toBe('Housekeeping');
    expect(sectionForResource('lost-found')).toBe('Housekeeping');
  });

  it('maps hr to RRHH and billing/payments to Billing', () => {
    expect(sectionForResource('hr')).toBe('RRHH');
    expect(sectionForResource('billing')).toBe('Billing');
  });

  it('maps reviews to PMS next to its nav item', () => {
    expect(sectionForResource('reviews')).toBe('PMS');
  });

  it('handles legacy crud codes and unknown resources defensively', () => {
    expect(sectionForResource('crud')).toBe('Sistema');
    expect(sectionForResource('unknown')).toBe('Sistema');
  });
});

describe('sectionForNavItem', () => {
  it('uses the tree slug prefix to bucket known groups', () => {
    expect(sectionForNavItem({ slug: 'gestion.pms.perfil', href: '/management/profile' })).toBe('PMS');
    expect(sectionForNavItem({ slug: 'gestion.reservas.tarifas', href: '/management/rates' })).toBe('CRS');
    expect(sectionForNavItem({ slug: 'gestion.housekeeping.mantenimiento' })).toBe('Housekeeping');
    expect(sectionForNavItem({ slug: 'gestion.rrhh.portal' })).toBe('RRHH');
    expect(sectionForNavItem({ slug: 'gestion.revenue.reportes' })).toBe('Revenue');
    expect(sectionForNavItem({ slug: 'gestion.billing.pagos' })).toBe('Billing');
    expect(sectionForNavItem({ slug: 'huesped.buscar' })).toBe('Cliente');
  });

  it('buckets system/admin/ownership slugs and hrefs into Sistema', () => {
    expect(sectionForNavItem({ slug: 'sistema.usuarios', href: '/system/users' })).toBe('Sistema');
    expect(sectionForNavItem({ slug: 'propietario.usuarios', href: '/ownership/users' })).toBe('Sistema');
    // fallback por href
    expect(sectionForNavItem({ href: '/admin/global-settings' })).toBe('Sistema');
  });

  it('buckets search/account hrefs into Cliente (fallback)', () => {
    expect(sectionForNavItem({ href: '/search' })).toBe('Cliente');
    expect(sectionForNavItem({ href: '/account/bookings' })).toBe('Cliente');
  });

  it('falls back to PMS for management items without a slug', () => {
    expect(sectionForNavItem({ href: '/management/profile' })).toBe('PMS');
  });
});

describe('computeNavVisibility (live top-down preview, no server round-trip)', () => {
  const tree = [
    { slug: 'gestion', parentSlug: null, permissionCode: null },
    { slug: 'gestion.reservas', parentSlug: 'gestion', permissionCode: 'reservations.read' },
    { slug: 'gestion.reservas.tarifas', parentSlug: 'gestion.reservas', permissionCode: 'rates.read' },
    { slug: 'gestion.reservas.informes', parentSlug: 'gestion.reservas', permissionCode: 'reports.tactical.read' },
    { slug: 'gestion.reservas.informes.adr', parentSlug: 'gestion.reservas.informes', permissionCode: 'reports.rates.adr.read' },
  ];

  it('marks a node visible when its code and ancestors are selected', () => {
    const vis = computeNavVisibility(tree, ['reservations.read', 'rates.read']);
    expect(vis.get('gestion.reservas')).toBe(true);
    expect(vis.get('gestion.reservas.tarifas')).toBe(true);
  });

  it('expands manage into the required read code', () => {
    const vis = computeNavVisibility(tree, ['reservations.manage', 'rates.read']);
    expect(vis.get('gestion.reservas.tarifas')).toBe(true);
  });

  it('hides a leaf whose area container is not satisfied (top-down pruning)', () => {
    // tiene el fino pero NO reports.tactical.read → el container Informes queda oculto
    const vis = computeNavVisibility(tree, ['reservations.read', 'reports.rates.adr.read']);
    expect(vis.get('gestion.reservas.informes')).toBe(false);
    expect(vis.get('gestion.reservas.informes.adr')).toBe(false);
  });

  it('hides descendants when an ancestor is missing', () => {
    const vis = computeNavVisibility(tree, ['rates.read']); // sin reservations.read
    expect(vis.get('gestion.reservas.tarifas')).toBe(false);
  });

  it('is visible for nodes requiring nothing', () => {
    const vis = computeNavVisibility(tree, []);
    expect(vis.get('gestion')).toBe(true);
  });

  it('is visible for the super-admin wildcard', () => {
    const vis = computeNavVisibility(tree, ['*.*']);
    expect(vis.get('gestion.reservas.informes.adr')).toBe(true);
  });
});
