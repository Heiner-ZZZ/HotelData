import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { ToastService } from '../../../../shared/services/toast.service';
import { GlobalSettingsApiService } from '../../services/global-settings-api.service';
import type { PlatformConfig } from '../../models/global-settings.model';
import { GlobalSettingsPageComponent } from './global-settings-page';

describe('GlobalSettingsPageComponent', () => {
  const config: PlatformConfig = {
    defaultCommissionPct: 5,
    defaultIvaPct: 16,
  };

  function setup() {
    const api = {
      updateConfig: jest.fn(() => of(config)),
      listHotels: jest.fn(() => of({ items: [], total: 0, totalPages: 0 })),
      createTaxRate: jest.fn(() => of({})),
      updateTaxRate: jest.fn(() => of({})),
      deleteTaxRate: jest.fn(() => of({})),
      createCommissionRate: jest.fn(() => of({})),
      updateCommissionRate: jest.fn(() => of({})),
      deleteCommissionRate: jest.fn(() => of({})),
    } as unknown as GlobalSettingsApiService;

    TestBed.configureTestingModule({
      imports: [GlobalSettingsPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: GlobalSettingsApiService, useValue: api },
      ],
    });
    const fixture = TestBed.createComponent(GlobalSettingsPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      toast: TestBed.inject(ToastService),
      http: TestBed.inject(HttpTestingController),
      api,
    };
  }

  it('envía el éxito de guardar la configuración al toast global (sin banner .message local)', () => {
    const { fixture, component, toast } = setup();
    // Los httpResource (config/tax-rates/commission-rates) quedan pendientes;
    // no son necesarios para el flujo de guardado.

    component.saveConfig();

    expect(toast.toasts().some(
      (t) => t.message === 'Configuración guardada correctamente' && t.type === 'success',
    )).toBe(true);
    expect(fixture.nativeElement.querySelector('.message')).toBeNull();
  });

  it('envía el error de guardar la configuración al toast global', () => {
    const { component, toast, api } = setup();
    (api.updateConfig as jest.Mock).mockReturnValue(throwError(() => new Error('boom')));

    component.saveConfig();

    expect(toast.toasts().some(
      (t) => t.message === 'Error al guardar la configuración' && t.type === 'error',
    )).toBe(true);
  });
});
