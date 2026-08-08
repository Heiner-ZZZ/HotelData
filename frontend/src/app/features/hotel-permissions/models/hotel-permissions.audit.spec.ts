import { permissionDiff, templatePermissionDiff } from './hotel-permissions.audit';
import type { HotelRole, RoleAuditEntry, RoleTemplate } from './hotel-permissions.model';

describe('hotel-permissions.audit', () => {
  describe('permissionDiff', () => {
    it('returns added and removed codes for a permissions change', () => {
      const entry: RoleAuditEntry = {
        timestamp: '2026-08-05T10:00:00Z',
        action: 'update',
        changedBy: 'gerente',
        summary: '',
        diff: {
          permissions: { old: ['dashboard.read', 'reservations.read'], new: ['dashboard.read', 'hr.read'] },
        },
      };

      const diff = permissionDiff(entry);

      expect(diff).toEqual({ added: ['hr.read'], removed: ['reservations.read'] });
    });

    it('returns null when the entry did not touch permissions', () => {
      const entry: RoleAuditEntry = {
        timestamp: '2026-08-05T10:00:00Z',
        action: 'update',
        changedBy: 'gerente',
        summary: '',
        diff: { display_name: { old: 'A', new: 'B' } },
      };

      expect(permissionDiff(entry)).toBeNull();
    });

    it('returns null when the diff has no permissions field', () => {
      const entry: RoleAuditEntry = {
        timestamp: '2026-08-05T10:00:00Z',
        action: 'update',
        changedBy: 'gerente',
        summary: '',
        diff: null,
      };

      expect(permissionDiff(entry)).toBeNull();
    });

    it('create entry: everything is added', () => {
      const entry: RoleAuditEntry = {
        timestamp: '2026-08-05T10:00:00Z',
        action: 'create',
        changedBy: 'gerente',
        summary: '',
        diff: { permissions: { old: [], new: ['dashboard.read', 'reservations.read'] } },
      };

      expect(permissionDiff(entry)).toEqual({ added: ['dashboard.read', 'reservations.read'], removed: [] });
    });
  });

  describe('templatePermissionDiff', () => {
    const templates: RoleTemplate[] = [
      { id: 'tpl1', roleName: 'recepcionista', displayName: 'Recepcionista', permissions: ['dashboard.read', 'reservations.read'] },
    ];

    const baseRole: HotelRole = {
      id: 'r1',
      propId: 1,
      name: 'recep_plaza',
      displayName: 'Recepción Plaza',
      permissions: ['dashboard.read', 'reservations.read', 'hr.read'],
      basedOnRoleId: 'tpl1',
      basedOn: 'recepcionista',
      isActive: true,
      isSystem: false,
      assignmentCount: 0,
      createdBy: 'gerente',
      createdAt: null,
      updatedAt: null,
    };

    it('diffs role permissions against its base template', () => {
      const diff = templatePermissionDiff(baseRole, templates);

      expect(diff).toEqual({ added: ['hr.read'], removed: [] });
    });

    it('returns null when the role has no base template', () => {
      const role = { ...baseRole, basedOnRoleId: null, basedOn: '' };
      expect(templatePermissionDiff(role, templates)).toBeNull();
    });

    it('returns null when the template is not in the list', () => {
      expect(templatePermissionDiff(baseRole, [])).toBeNull();
    });

    it('detects permissions removed from the template', () => {
      const role = { ...baseRole, permissions: ['dashboard.read'] };
      expect(templatePermissionDiff(role, templates)).toEqual({
        added: [],
        removed: ['reservations.read'],
      });
    });
  });
});
