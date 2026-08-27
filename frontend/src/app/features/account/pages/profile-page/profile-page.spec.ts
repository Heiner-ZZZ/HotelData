import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of, Subject } from 'rxjs';

import { baseUrlInterceptor } from '../../../../core/api/base-url.interceptor';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { ProfileApiService } from '../../services/profile-api.service';
import type { ProfileDto } from '../../models/profile.dto';
import type { ProfileViewModel } from '../../models/profile.model';
import { mapProfileDtoToViewModel } from '../../mappers/profile.mapper';
import { ProfilePageComponent } from './profile-page';

/** DTO mínimo pero completo que devuelve el backend en GET /account/profile. */
function makeDto(overrides: Partial<ProfileDto> = {}): ProfileDto {
  return {
    user_id: 'u-1',
    username: 'jperez',
    email: 'jperez@hotel.test',
    display_name: 'Juan Pérez',
    primary_role: 'gerente_hotel',
    primary_role_id: 'role-gerente',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    phone: '+51999000111',
    notification_email: 'jperez@hotel.test',
    address_street: 'Av. Central 123',
    address_city: 'Lima',
    address_state: 'Lima',
    address_country: 'PE',
    address_postal_code: '15001',
    date_of_birth: '1990-05-20',
    nationality: 'Peruana',
    id_document_type: 'dni',
    id_document_number: '12345678',
    preferred_language: 'es',
    marketing_opt_in: false,
    notification_email_enabled: true,
    notification_sms_enabled: false,
    avatar_url: '',
    social_instagram: '',
    social_facebook: '',
    social_twitter: '',
    social_linkedin: '',
    travel_purpose: '',
    travel_budget: '',
    travel_companions: '',
    travel_accommodation: '',
    travel_destination_type: '',
    travel_interests: '',
    travel_frequent_flyer: '',
    travel_loyalty_programs: '',
    travel_notes: '',
    ...overrides,
  };
}

describe('ProfilePageComponent — modo CRUD del nav', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as never;

    const api = { updateProfile: jest.fn(), uploadAvatar: jest.fn() };
    const toast = { success: jest.fn(), error: jest.fn() };
    const auth = {
      updateAvatar: jest.fn(),
      isAuthenticated: jest.fn(() => true),
      sessionLoaded: jest.fn(() => true),
      invalidateSession: jest.fn(),
    };

    TestBed.configureTestingModule({
      imports: [ProfilePageComponent],
      providers: [
        provideHttpClient(withInterceptors([baseUrlInterceptor])),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: { get: () => null } } },
        },
        { provide: ProfileApiService, useValue: api },
        { provide: AuthService, useValue: auth },
        { provide: ToastService, useValue: toast },
      ],
    });

    const fixture = TestBed.createComponent(ProfilePageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      mode: TestBed.inject(OperationModeService),
      http: TestBed.inject(HttpTestingController),
      api,
      toast,
    };
  }

  /** Seed the httpResource GET /account/profile and let it publish. */
  async function seedProfile(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }, dto: ProfileDto) {
    ctx.http.expectOne('/api/account/profile').flush(dto);
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

  function editField(ctx: { component: { form: { controls: { displayName: { setValue(v: string): void } } } }; fixture: { detectChanges(): void } }, value: string) {
    ctx.component.form.controls.displayName.setValue(value);
    ctx.fixture.detectChanges();
  }

  function pageEl(ctx: { fixture: { nativeElement: HTMLElement } }) {
    return ctx.fixture.nativeElement as HTMLElement;
  }

  it('parte en modo Solo lectura cuando el form coincide con el perfil cargado', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto());

    expect(ctx.mode.mode()).toBe('read');
    expect(pageEl(ctx).querySelector('.form-footer .unsaved-dot')).toBeNull();
    expect(pageEl(ctx).querySelector('.form-status')).toBeNull();
    expect(pageEl(ctx).querySelector('form.profile-form')?.classList.contains('mode-active')).toBe(false);
  });

  it('cambia el chip a Editando al modificar un campo (cambios sin guardar)', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto());

    editField(ctx, 'Ana Gómez');

    expect(ctx.mode.mode()).toBe('update');
    expect(ctx.mode.detail()).toBe('Perfil');
    // Señales en la propia página para que el usuario sepa en qué modo está.
    expect(pageEl(ctx).querySelector('.form-footer .unsaved-dot')).not.toBeNull();
    expect(pageEl(ctx).querySelector('.form-status')?.textContent).toContain('cambios sin guardar');
    expect(pageEl(ctx).querySelector('form.profile-form')?.classList.contains('mode-active')).toBe(true);
  });

  it('vuelve a Solo lectura al revertir el cambio', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto());

    editField(ctx, 'Ana Gómez');
    expect(ctx.mode.mode()).toBe('update');

    editField(ctx, 'Juan Pérez');

    expect(ctx.mode.mode()).toBe('read');
    expect(pageEl(ctx).querySelector('.form-footer .unsaved-dot')).toBeNull();
    expect(pageEl(ctx).querySelector('.form-status')).toBeNull();
  });

  it('vuelve a Solo lectura tras guardar correctamente', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto());

    editField(ctx, 'Ana Gómez');
    expect(ctx.mode.mode()).toBe('update');

    const updated: ProfileViewModel = { ...mapProfileDtoToViewModel(makeDto()), displayName: 'Ana Gómez' };
    ctx.api.updateProfile.mockReturnValue(of(updated));

    ctx.component.save();
    await flush();
    ctx.fixture.detectChanges();

    expect(ctx.toast.success).toHaveBeenCalledWith('Perfil actualizado correctamente.');
    expect(ctx.mode.mode()).toBe('read');
    expect(pageEl(ctx).querySelector('.form-footer .unsaved-dot')).toBeNull();
    expect(pageEl(ctx).querySelector('.form-status')).toBeNull();
  });

  function toggleHeadings(ctx: { fixture: { nativeElement: HTMLElement } }): string[] {
    return [...pageEl(ctx).querySelectorAll('.toggle-group h3')].map((h) => h.textContent?.trim() ?? '');
  }

  it('oculta la sección de Publicidad y promociones para staff (el consentimiento de marketing es del huésped)', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto()); // primary_role: gerente_hotel
    ctx.component.handleSetTab('preferences');
    ctx.fixture.detectChanges();

    const headings = toggleHeadings(ctx);
    expect(headings).toContain('Notificaciones');
    expect(headings).not.toContain('Publicidad y promociones');
  });

  it('muestra la sección de Publicidad y promociones solo para huéspedes (cliente)', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto({ primary_role: 'cliente' }));
    ctx.component.handleSetTab('preferences');
    ctx.fixture.detectChanges();

    const headings = toggleHeadings(ctx);
    expect(headings).toContain('Notificaciones');
    expect(headings).toContain('Publicidad y promociones');
  });

  it('agrega la pestaña Promociones para huéspedes (cliente)', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto({ primary_role: 'cliente' }));
    const tabs = ctx.component.tabs().map(t => t.key);
    expect(tabs).toContain('promotions');
    expect(tabs).toContain('preferences');
  });

  it('no muestra la pestaña Promociones para staff', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto()); // gerente_hotel
    expect(ctx.component.tabs().map(t => t.key)).not.toContain('promotions');
  });

  it('renderiza la pestaña Promociones fuera del form de perfil (lista read-only)', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto({ primary_role: 'cliente' }));

    ctx.component.handleSetTab('promotions');
    ctx.fixture.detectChanges();
    // La pestaña lanza su httpResource al montar: resolverlo (filtrado por tipo).
    ctx.http
      .expectOne('/api/notifications/my?notification_type=guest_promotional&page=1&page_size=10')
      .flush({
        items: [], total: 0, unread_count: 0, page: 1, page_size: 10, total_pages: 1,
      });
    await flush();
    ctx.fixture.detectChanges();

    // La lista de promociones vive FUERA del form (sin botón Guardar cambios).
    expect(pageEl(ctx).querySelector('form.profile-form')).toBeNull();
    expect(pageEl(ctx).querySelector('app-pp-promotions-tab')).not.toBeNull();
    expect(ctx.component.activeTab()).toBe('promotions');
  });

  it('mantiene el modo Editando al cambiar de pestaña (contact/preferences)', async () => {
    const ctx = setup();
    await seedProfile(ctx, makeDto());

    editField(ctx, 'Ana Gómez');
    expect(ctx.mode.mode()).toBe('update');

    ctx.component.handleSetTab('contact');
    ctx.fixture.detectChanges();

    expect(ctx.component.activeTab()).toBe('contact');
    expect(ctx.mode.mode()).toBe('update');

    ctx.component.handleSetTab('preferences');
    ctx.fixture.detectChanges();

    expect(ctx.component.activeTab()).toBe('preferences');
    expect(ctx.mode.mode()).toBe('update');
  });
});
