import { TestBed } from '@angular/core/testing';

import { CarouselControlsComponent } from './carousel-controls';

async function render(inputs: Record<string, unknown>) {
  TestBed.resetTestingModule();
  await TestBed.configureTestingModule({
    imports: [CarouselControlsComponent],
  }).compileComponents();

  const fixture = TestBed.createComponent(CarouselControlsComponent);
  for (const [key, value] of Object.entries(inputs)) {
    fixture.componentRef.setInput(key, value);
  }
  fixture.detectChanges();
  return fixture;
}

describe('CarouselControlsComponent (puntitos + flechas compartidos)', () => {
  it('no renderiza nada con count <= 1', async () => {
    const fixture = await render({ count: 1, activeIndex: 0 });
    expect(fixture.nativeElement.querySelectorAll('.cc-dot').length).toBe(0);
    expect(fixture.nativeElement.querySelectorAll('.cc-arrow').length).toBe(0);
  });

  it('renderiza count puntitos y el activo es la píldora (is-active)', async () => {
    const fixture = await render({ count: 4, activeIndex: 2 });
    const dots = fixture.nativeElement.querySelectorAll('.cc-dot');
    expect(dots.length).toBe(4);
    expect(dots[2].classList.contains('is-active')).toBe(true);
    expect(dots[0].classList.contains('is-active')).toBe(false);
  });

  it('emite navigate con el índice al hacer clic en un puntito', async () => {
    const fixture = await render({ count: 3, activeIndex: 0 });
    const navigate = jest.spyOn(fixture.componentInstance.navigate, 'emit');
    (fixture.nativeElement as HTMLElement).querySelectorAll('.cc-dot')[2].dispatchEvent(
      new MouseEvent('click', { bubbles: true, cancelable: true }),
    );
    expect(navigate).toHaveBeenCalledWith(2);
  });

  it('emite previous/next con las flechas', async () => {
    const fixture = await render({ count: 3, activeIndex: 1 });
    const previous = jest.spyOn(fixture.componentInstance.previous, 'emit');
    const next = jest.spyOn(fixture.componentInstance.next, 'emit');

    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.cc-prev')!.click();
    expect(previous).toHaveBeenCalled();

    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.cc-next')!.click();
    expect(next).toHaveBeenCalled();
  });

  it('detiene la propagación del clic (para contenedores <a>)', async () => {
    const fixture = await render({ count: 3, activeIndex: 0 });
    const docListener = jest.fn();
    document.addEventListener('click', docListener);
    try {
      (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.cc-dot')!.click();
      expect(docListener).not.toHaveBeenCalled();
    } finally {
      document.removeEventListener('click', docListener);
    }
  });

  it('en modo reveal marca el host y acepta .revealed (el CSS de opacidad se verifica en navegador)', async () => {
    // jsdom no inyecta el SCSS de los componentes, así que el contrato que
    // se verifica aquí es el de clases del que depende el CSS: con
    // `revealOnHover` el host lleva `reveal-mode`, y el padre puede revelar
    // las flechas añadiendo `revealed` al host. El efecto visual (opacity
    // 0 → 1 con transición) se valida en vivo en el navegador.
    const fixture = await render({ count: 3, activeIndex: 0, revealOnHover: true });
    const host = fixture.nativeElement as HTMLElement;
    expect(host.classList.contains('reveal-mode')).toBe(true);

    host.classList.add('revealed');
    expect(host.classList.contains('revealed')).toBe(true);

    // Sin reveal-mode, el host no arrastra la clase (modo siempre visible).
    const plain = await render({ count: 3, activeIndex: 0 });
    expect((plain.nativeElement as HTMLElement).classList.contains('reveal-mode')).toBe(false);
  });

  it('usa aria-labels con el subjectLabel', async () => {
    const fixture = await render({ count: 3, activeIndex: 0, subjectLabel: 'Hotel Lima' });
    const prev = fixture.nativeElement.querySelector<HTMLElement>('.cc-prev')!;
    const next = fixture.nativeElement.querySelector<HTMLElement>('.cc-next')!;
    const dot = fixture.nativeElement.querySelectorAll<HTMLElement>('.cc-dot')[0]!;
    expect(prev.getAttribute('aria-label')).toContain('Hotel Lima');
    expect(next.getAttribute('aria-label')).toContain('Hotel Lima');
    expect(dot.getAttribute('aria-label')).toContain('Hotel Lima');
  });
});
