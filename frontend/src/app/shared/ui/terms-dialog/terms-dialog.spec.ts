import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { TermsDialogComponent } from './terms-dialog';

const LEGAL_DTO = {
  doc_type: 'terms_guest',
  version: 2,
  title: 'Términos y Condiciones para Huéspedes',
  effective_date: '2026-08-15T00:00:00+00:00',
  sections: [
    { heading: '1. Aceptación', body: 'Al crear una cuenta aceptas estos términos.' },
    { heading: '2. Reservas', body: 'Los precios mostrados corresponden a las tarifas vigentes.' },
  ],
};

describe('TermsDialogComponent', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  function setup(docType = 'terms_guest', open = true) {
    TestBed.configureTestingModule({
      imports: [TermsDialogComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(TermsDialogComponent);
    fixture.componentRef.setInput('docType', docType);
    fixture.componentRef.setInput('open', open);
    fixture.detectChanges();
    return { fixture, http: TestBed.inject(HttpTestingController) };
  }

  it('no renderiza nada cuando está cerrado y no dispara request', () => {
    const { fixture } = setup('terms_guest', false);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.terms-dialog')).toBeNull();
  });

  it('carga el documento activo del backend y renderiza título, versión y secciones', async () => {
    const { fixture, http } = setup('terms_guest', true);
    const req = http.expectOne((r) =>
      r.url.includes('/public/legal') && r.url.includes('doc_type=terms_guest'),
    );
    req.flush(LEGAL_DTO);
    await fixture.whenStable();
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.terms-dialog')).toBeTruthy();
    expect(el.querySelector('h2')?.textContent).toContain('Términos y Condiciones para Huéspedes');
    expect(el.querySelector('.terms-version')?.textContent).toContain('Versión 2');
    const sections = el.querySelectorAll('.terms-section');
    expect(sections.length).toBe(2);
    expect(sections[0].querySelector('h3')?.textContent).toContain('1. Aceptación');
    expect(sections[0].querySelector('p')?.textContent).toContain('aceptas estos términos');
  });

  it('muestra estado de error con reintento cuando el backend falla', async () => {
    const { fixture, http } = setup('terms_guest', true);
    const req = http.expectOne((r) => r.url.includes('/public/legal'));
    req.flush(
      { detail: 'No hay una versión publicada.' },
      { status: 404, statusText: 'Not Found' },
    );
    await fixture.whenStable();
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.terms-state')).toBeTruthy();
    expect(el.querySelector('.terms-retry')).toBeTruthy();
  });

  it('el botón Entendido emite close', async () => {
    const { fixture, http } = setup('terms_guest', true);
    http.expectOne((r) => r.url.includes('/public/legal')).flush(LEGAL_DTO);
    await fixture.whenStable();
    fixture.detectChanges();

    let closed = false;
    fixture.componentInstance.close.subscribe(() => (closed = true));
    const done = fixture.nativeElement.querySelector('.terms-done') as HTMLButtonElement;
    done.click();
    expect(closed).toBe(true);
  });
});
