import { TestBed } from '@angular/core/testing';

import { OperationModeService } from '../../../core/services/operation-mode.service';
import { ConfirmDialogService } from './confirm-dialog.service';

describe('ConfirmDialogService', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        {
          provide: OperationModeService,
          useValue: { setTransientMode: jest.fn(() => () => undefined) },
        },
      ],
    });
    return TestBed.inject(ConfirmDialogService);
  }

  it('openPrompt resuelve el valor del input al confirmar', async () => {
    const service = setup();
    const promise = service.openPrompt({
      title: 'Reembolsar pago',
      message: '¿Reembolsar?',
      confirmLabel: 'Reembolsar',
      input: { label: 'Motivo (opcional)' },
    });

    service.inputValue.set('Cobro duplicado');
    service.confirm();

    await expect(promise).resolves.toBe('Cobro duplicado');
  });

  it('openPrompt resuelve null al cancelar', async () => {
    const service = setup();
    const promise = service.openPrompt({
      title: 'Reembolsar pago',
      message: '¿Reembolsar?',
      confirmLabel: 'Reembolsar',
      input: { label: 'Motivo (opcional)' },
    });

    service.cancel();

    await expect(promise).resolves.toBeNull();
  });

  it('open() sin input sigue resolviendo boolean al confirmar (compatibilidad)', async () => {
    const service = setup();
    const promise = service.open({ title: 'Anular', message: '¿Anular?' });

    service.confirm();

    await expect(promise).resolves.toBe(true);
  });

  it('open() sin input resuelve false al cancelar (compatibilidad)', async () => {
    const service = setup();
    const promise = service.open({ title: 'Anular', message: '¿Anular?' });

    service.cancel();

    await expect(promise).resolves.toBe(false);
  });

  it('openPrompt inicializa inputValue con el initialValue del config', () => {
    const service = setup();

    service.openPrompt({
      title: 'Reembolsar',
      message: '¿Reembolsar?',
      input: { label: 'Motivo', initialValue: 'Cobro duplicado' },
    });

    expect(service.inputValue()).toBe('Cobro duplicado');
  });
});
