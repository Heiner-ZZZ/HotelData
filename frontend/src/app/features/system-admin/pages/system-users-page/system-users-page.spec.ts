import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { SystemUsersApiService } from '../../services/system-users-api.service';
import type { SystemUsersResponseDto } from '../../models/system-users.dto';
import { SystemUsersPageComponent } from './system-users-page';

describe('SystemUsersPageComponent', () => {
  const usersResponse: SystemUsersResponseDto = {
    counts: { users: 2, roles: 2 },
    current_user: { username: 'superadmin', primary_role: 'super_admin' },
    users: [
      {
        user_id: 'a1',
        username: 'gerente1',
        email: 'gerente1@example.com',
        display_name: 'Gerente Uno',
        primary_role: 'admin_sistema',
        role_names: ['admin_sistema'],
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
        is_current_user: false,
        is_protected: false,
        can_toggle: true,
        toggle_label: 'Desactivar',
        action_hint: '',
      },
      {
        user_id: 'a2',
        username: 'superadmin',
        email: 'admin@hoteldata.local',
        display_name: 'Super Admin',
        primary_role: 'super_admin',
        role_names: ['super_admin'],
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
        is_current_user: true,
        is_protected: true,
        can_toggle: false,
        toggle_label: 'Desactivar',
        action_hint: 'Sesión actual',
      },
    ],
    roles: [
      { role_name: 'admin_sistema', description: 'Administra la configuración del sistema' },
      { role_name: 'super_admin', description: 'Acceso total al sistema' },
    ],
  };

  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as never;

    const api = {
      toggleUserActive: jest.fn(),
      deleteUser: jest.fn(),
      updateUser: jest.fn(),
      searchHotels: jest.fn(),
    };
    const toast = { success: jest.fn(), error: jest.fn() };

    TestBed.configureTestingModule({
      imports: [SystemUsersPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        { provide: SystemUsersApiService, useValue: api },
        { provide: ToastService, useValue: toast },
      ],
    });

    const fixture = TestBed.createComponent(SystemUsersPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    return {
      fixture,
      component,
      mode: TestBed.inject(OperationModeService),
      http: TestBed.inject(HttpTestingController),
      api,
      toast,
    };
  }

  /** Seed the httpResource list response (published async). */
  async function seedUsers(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }) {
    ctx.http.expectOne('/api/admin/users').flush(usersResponse);
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

  it('starts in read mode', () => {
    const { mode } = setup();
    expect(mode.mode()).toBe('read');
  });

  it('switches the nav chip to update mode with the username when editing', async () => {
    const { component, mode, http, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);

    expect(mode.mode()).toBe('update');
    expect(mode.detail()).toBe('gerente1');
  });

  it('restores read mode when the modal closes', async () => {
    const { component, mode, http, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    expect(mode.mode()).toBe('update');

    component.closeEdit();
    expect(mode.mode()).toBe('read');
  });

  it('pre-fills the form with the user data', async () => {
    const { component, http, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);

    expect(component.editForm()).toEqual({
      username: 'gerente1',
      displayName: 'Gerente Uno',
      email: 'gerente1@example.com',
      primaryRole: 'admin_sistema',
      password: '',
      assignedHotels: [],
    });
  });

  it('exposes role options for the select', async () => {
    const { component, http, fixture } = setup();
    await seedUsers({ http, fixture });

    expect(component.roleOptions().map((r) => r.roleName)).toEqual(['admin_sistema', 'super_admin']);
  });

  it('marks current/protected users as not editable', async () => {
    const { component, http, fixture } = setup();
    await seedUsers({ http, fixture });

    const gerente = component.filteredItems().find((u) => u.userId === 'a1')!;
    const superadmin = component.filteredItems().find((u) => u.userId === 'a2')!;
    expect(gerente.canEdit).toBe(true);
    expect(superadmin.canEdit).toBe(false);
  });

  it('saves the edit and shows a success toast', async () => {
    const { component, mode, http, api, toast, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({ ...f, displayName: 'Gerente Renombrado' }));

    const pending = new Subject<{ ok: boolean; message: string }>();
    api.updateUser.mockReturnValue(pending);

    component.saveEdit();

    expect(api.updateUser).toHaveBeenCalledWith('a1', {
      username: 'gerente1',
      display_name: 'Gerente Renombrado',
      email: 'gerente1@example.com',
      primary_role: 'admin_sistema',
    });

    pending.next({ ok: true, message: 'Usuario gerente1 actualizado correctamente.' });
    pending.complete();
    await flush();

    expect(toast.success).toHaveBeenCalledWith('Usuario gerente1 actualizado correctamente.');
    expect(component.editingUser()).toBeNull();
    expect(mode.mode()).toBe('read');
  });

  it('includes the password in the payload only when provided', async () => {
    const { component, http, api, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({ ...f, password: 'Nueva123!' }));

    api.updateUser.mockReturnValue({ subscribe: () => ({}) });
    component.saveEdit();

    expect(api.updateUser).toHaveBeenCalledWith(
      'a1',
      expect.objectContaining({ password: 'Nueva123!' })
    );
  });

  it('rejects an invalid email with a toast and no API call', async () => {
    const { component, http, api, toast, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({ ...f, email: 'correo-invalido' }));

    component.saveEdit();

    expect(api.updateUser).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('Formato de email inválido.');
  });

  it('rejects a short password with a toast and no API call', async () => {
    const { component, http, api, toast, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({ ...f, password: '123' }));

    component.saveEdit();

    expect(api.updateUser).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('La contraseña debe tener al menos 6 caracteres.');
  });

  it('shows an error toast when the API rejects', async () => {
    const { component, http, api, toast, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);

    const pending = new Subject<{ ok: boolean; message: string }>();
    api.updateUser.mockReturnValue(pending);

    component.saveEdit();
    pending.error({ error: { message: 'El email ya está registrado por otro usuario.' } });

    await flush();

    expect(toast.error).toHaveBeenCalledWith('El email ya está registrado por otro usuario.');
    expect(component.editingUser()).not.toBeNull();
  });

  // ── Username ────────────────────────────────────────────────────────────

  it('rejects an empty username with a toast and no API call', async () => {
    const { component, http, api, toast, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({ ...f, username: '   ' }));

    component.saveEdit();

    expect(api.updateUser).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('El nombre de usuario no puede quedar vacío.');
  });

  it('rejects a username with spaces', async () => {
    const { component, http, api, toast, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({ ...f, username: 'con espacios' }));

    component.saveEdit();

    expect(api.updateUser).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('El nombre de usuario no puede contener espacios.');
  });

  it('sends the username in the payload when changed', async () => {
    const { component, http, api, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({ ...f, username: 'gerente_nuevo' }));

    api.updateUser.mockReturnValue({ subscribe: () => ({}) });
    component.saveEdit();

    expect(api.updateUser).toHaveBeenCalledWith('a1', expect.objectContaining({ username: 'gerente_nuevo' }));
  });

  // ── Hoteles asignados (roles de hotel) ─────────────────────────────────

  it('identifies hotel roles', () => {
    const { component } = setup();
    expect(component.isHotelRole('gerente_hotel')).toBe(true);
    expect(component.isHotelRole('recepcionista')).toBe(false);
    expect(component.isHotelRole('maintenance')).toBe(true);
  });

  it('pre-fills assigned hotels from the user', async () => {
    const { component, http, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit({ ...editable, assignedHotels: [{ propId: 1, label: 'Hotel Lima Centro' }] });

    expect(component.editForm().assignedHotels).toEqual([{ propId: 1, label: 'Hotel Lima Centro' }]);
  });

  it('toggles hotels in and out of the selection', async () => {
    const { component, http, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);

    component.toggleHotel({ propId: 1, label: 'Hotel Lima Centro' });
    expect(component.isHotelSelected(1)).toBe(true);
    expect(component.editForm().assignedHotels).toHaveLength(1);

    component.toggleHotel({ propId: 1, label: 'Hotel Lima Centro' });
    expect(component.isHotelSelected(1)).toBe(false);
    expect(component.editForm().assignedHotels).toHaveLength(0);
  });

  it('removes a hotel chip by id', async () => {
    const { component, http, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit({ ...editable, assignedHotels: [{ propId: 1, label: 'Hotel Lima Centro' }] });

    component.removeHotel(1);
    expect(component.editForm().assignedHotels).toHaveLength(0);
  });

  it('requires at least one hotel for hotel roles', async () => {
    const { component, http, api, toast, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({ ...f, primaryRole: 'gerente_hotel' }));

    component.saveEdit();

    expect(api.updateUser).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalledWith('Un usuario con rol de hotel debe tener al menos un hotel asignado.');
  });

  it('sends assigned_hotels in the payload for hotel roles', async () => {
    const { component, http, api, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({
      ...f,
      primaryRole: 'gerente_hotel',
      assignedHotels: [{ propId: 1, label: 'Hotel Lima Centro' }],
    }));

    api.updateUser.mockReturnValue({ subscribe: () => ({}) });
    component.saveEdit();

    expect(api.updateUser).toHaveBeenCalledWith(
      'a1',
      expect.objectContaining({ assigned_hotels: [1] })
    );
  });

  it('does not send assigned_hotels for non-hotel roles', async () => {
    const { component, http, api, fixture } = setup();
    await seedUsers({ http, fixture });

    const editable = component.filteredItems().find((u) => u.userId === 'a1')!;
    component.openEdit(editable);
    component.editForm.update((f) => ({ ...f, assignedHotels: [{ propId: 1, label: 'Hotel Lima Centro' }] }));

    api.updateUser.mockReturnValue({ subscribe: () => ({}) });
    component.saveEdit();

    const payload = api.updateUser.mock.calls[0][1];
    expect(payload).not.toHaveProperty('assigned_hotels');
  });
});
