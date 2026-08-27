import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { RegisterPageComponent } from './register-page';

const LEGAL_DTO = {
  doc_type: 'terms_guest',
  version: 1,
  title: 'Términos y Condiciones para Huéspedes',
  effective_date: '2026-08-16T21:17:11.750000',
  sections: [{ heading: '1. Aceptación', body: 'Al crear una cuenta aceptas estos términos.' }],
};

describe('RegisterPageComponent — paso de verificación de código', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  function setupInVerificationStep() {
    TestBed.configureTestingModule({
      imports: [RegisterPageComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(RegisterPageComponent);
    fixture.detectChanges();
    TestBed.inject(HttpTestingController)
      .expectOne((r) => r.url.includes('/public/legal') && r.url.includes('doc_type=terms_guest'))
      .flush(LEGAL_DTO);

    const component = fixture.componentInstance;
    component.registerForm.controls.email.setValue('juan@correo.com');
    component.verificationEmail.set('juan@correo.com');
    component.codeSent.set(true);
    component.awaitingVerification.set(true);
    fixture.detectChanges();

    return { fixture, component, http: TestBed.inject(HttpTestingController) };
  }

  function typeCode(fixture: ReturnType<typeof setupInVerificationStep>['fixture'], code: string) {
    const el = fixture.nativeElement as HTMLElement;
    const inputs = el.querySelectorAll<HTMLInputElement>('.code-input');
    expect(inputs.length).toBe(6);
    code.split('').forEach((digit, i) => {
      inputs[i].value = digit;
      inputs[i].dispatchEvent(new Event('input'));
    });
  }

  function completeRegistrationFields(fixture: ReturnType<typeof setupInVerificationStep>['fixture']) {
    const el = fixture.nativeElement as HTMLElement;
    const set = (selector: string, value: string) => {
      const input = el.querySelector<HTMLInputElement>(selector);
      expect(input).not.toBeNull();
      if (!input) throw new Error(`no se encontró ${selector}`);
      input.value = value;
      input!.dispatchEvent(new Event('input'));
    };
    set('input[formcontrolname="username"]', 'juanperez');
    set('input[formcontrolname="password"]', 'secreto123');
    set('input[formcontrolname="confirm_password"]', 'secreto123');

    const terms = el.querySelector<HTMLInputElement>('input[type="checkbox"]');
    expect(terms).not.toBeNull();
    if (!terms) throw new Error('checkbox de términos no visible');
    if (!terms.checked) terms.click();
  }

  it('habilita "Verificar y crear cuenta" cuando el código está completo y el formulario es válido', () => {
    const { fixture } = setupInVerificationStep();
    typeCode(fixture, '482193');
    completeRegistrationFields(fixture);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const button = el.querySelector<HTMLButtonElement>('.code-submit');
    expect(button).not.toBeNull();
    if (!button) throw new Error('botón Verificar y crear cuenta no visible');
    expect(button.disabled).toBe(false);
  });

  it('mantiene el botón deshabilitado mientras el código esté incompleto', () => {
    const { fixture } = setupInVerificationStep();
    typeCode(fixture, '48219');
    completeRegistrationFields(fixture);
    fixture.detectChanges();

    const button = (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('.code-submit');
    expect(button!.disabled).toBe(true);
  });

  it('limpia los dígitos del código al reenviar, para evitar enviar el código viejo', async () => {
    const { fixture, component, http } = setupInVerificationStep();
    typeCode(fixture, '482193');
    fixture.detectChanges();

    // El viejo código debe estar presente antes de reenviar
    expect(component.codeDigits()).toEqual(['4', '8', '2', '1', '9', '3']);

    component.resendCode();

    // El request POST a send-code debe dispararse
    const sendReq = http.expectOne((r) => r.url.includes('/auth/send-code'));
    expect(sendReq.request.body.email).toBe('juan@correo.com');

    // Los dígitos deben estar vacíos inmediatamente, sin esperar respuesta
    expect(component.codeDigits()).toEqual(['', '', '', '', '', '']);

    // Los controles del formulario codeForm también deben limpiarse
    const controls = component.codeForm.controls;
    expect(controls.digit0.value).toBe('');
    expect(controls.digit1.value).toBe('');
    expect(controls.digit2.value).toBe('');
    expect(controls.digit3.value).toBe('');
    expect(controls.digit4.value).toBe('');
    expect(controls.digit5.value).toBe('');

    // El primer input debe recibir el foco para empezar a teclear sin clic extra
    const focusedEl = document.activeElement as HTMLInputElement;
    expect(focusedEl?.id).toBe('code-digit-0');

    sendReq.flush({ ok: true, email: 'juan@correo.com', message: 'Nuevo código enviado.' });
    await fixture.whenStable();
  });

  it('envía confirm-code al backend al hacer clic con todo válido', async () => {
    const { fixture, component, http } = setupInVerificationStep();
    typeCode(fixture, '482193');
    completeRegistrationFields(fixture);
    fixture.detectChanges();

    const button = (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('.code-submit');
    button!.click();
    await fixture.whenStable();

    const req = http.expectOne((r) => r.url.includes('/auth/confirm-code'));
    expect(req.request.body).toEqual({
      email: 'juan@correo.com',
      code: '482193',
      username: 'juanperez',
      password: 'secreto123',
      display_name: undefined,
    });
    req.flush({ ok: true, message: 'Cuenta verificada' });
    await fixture.whenStable();
    expect(component.successMessage()).toContain('verificada');
  });
});
