import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideRouter } from '@angular/router';

import {
  ActiveTurnoService,
  type TurnoKind,
  type TurnoChipViewModel,
} from '../../services/active-turno.service';
import { TurnoChipComponent } from './turno-chip';

const CAJA_VM: TurnoChipViewModel = {
  kind: 'caja',
  icon: 'point_of_sale',
  title: 'Turno actual',
  chipLabel: 'T01 · 08:00–16:00',
  typeLabel: 'Turno Matutino',
  dateLabel: '15 Ago',
  windowLabel: '08:00–16:00',
  startLabel: '08:00',
  endLabel: '16:00',
  statusLabel: 'Abierto',
  statusTone: 'ok',
  operatorLabel: 'Recep. Prueba',
  hasShift: true,
  cta: null,
};

const NO_SHIFT_VM: TurnoChipViewModel = {
  kind: 'caja',
  icon: 'point_of_sale',
  title: 'Turno actual',
  chipLabel: 'Sin turno',
  typeLabel: 'Caja',
  dateLabel: '',
  windowLabel: '',
  startLabel: '—',
  endLabel: '—',
  statusLabel: 'Sin turno',
  statusTone: 'neutral',
  operatorLabel: '—',
  hasShift: false,
  cta: { label: 'Abrir turno', href: '/management/shifts' },
};

describe('TurnoChipComponent', () => {
  let fixture: ComponentFixture<TurnoChipComponent>;
  let serviceMock: {
    viewModel: ReturnType<typeof signal<TurnoChipViewModel | null>>;
    isLoading: ReturnType<typeof signal<boolean>>;
    hasError: ReturnType<typeof signal<boolean>>;
    hasMultiple: ReturnType<typeof signal<boolean>>;
    activeKind: ReturnType<typeof signal<TurnoKind>>;
    cycleKind: jest.Mock;
  };

  function createFixture() {
    fixture = TestBed.createComponent(TurnoChipComponent);
    fixture.detectChanges();
  }

  beforeEach(async () => {
    serviceMock = {
      viewModel: signal<TurnoChipViewModel | null>(CAJA_VM),
      isLoading: signal(false),
      hasError: signal(false),
      hasMultiple: signal(false),
      activeKind: signal<TurnoKind>('caja'),
      cycleKind: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [TurnoChipComponent],
      providers: [
        provideRouter([]),
        { provide: ActiveTurnoService, useValue: serviceMock },
      ],
    }).compileComponents();
  });

  it('renders the chip label for a caja turno', () => {
    createFixture();
    const label = fixture.nativeElement.querySelector('.turno-chip-label') as HTMLElement;
    expect(label.textContent).toBe('T01 · 08:00–16:00');
    const trigger = fixture.nativeElement.querySelector('.turno-chip') as HTMLElement;
    expect(trigger.getAttribute('aria-label')).toContain('T01 · 08:00–16:00');
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
  });

  it('hides the ">" cycle button when the user has a single turno kind', () => {
    createFixture();
    expect(fixture.nativeElement.querySelector('.turno-cycle')).toBeNull();
  });

  it('shows the ">" cycle button and cycles when both kinds are available', () => {
    serviceMock.hasMultiple.set(true);
    createFixture();

    const cycle = fixture.nativeElement.querySelector('.turno-cycle') as HTMLElement;
    expect(cycle).not.toBeNull();
    expect(cycle.getAttribute('aria-label')).toBe('Ver mi turno de asistencia');

    cycle.click();
    expect(serviceMock.cycleKind).toHaveBeenCalledTimes(1);
  });

  it('opens the detail popover on click with Inicio/Fin/Estado/Operador rows', () => {
    createFixture();
    const trigger = fixture.nativeElement.querySelector('.turno-chip') as HTMLElement;
    trigger.click();
    fixture.detectChanges();

    const popover = fixture.nativeElement.querySelector('.turno-popover') as HTMLElement;
    expect(popover).not.toBeNull();
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
    const text = popover.textContent ?? '';
    expect(text).toContain('Turno Matutino');
    expect(text).toContain('15 Ago · 08:00–16:00');
    expect(text).toContain('Inicio');
    expect(text).toContain('08:00');
    expect(text).toContain('Fin');
    expect(text).toContain('16:00');
    expect(text).toContain('Estado');
    expect(text).toContain('Abierto');
    expect(text).toContain('Operador');
    expect(text).toContain('Recep. Prueba');
  });

  it('renders the "Abrir turno" CTA when there is no open shift', () => {
    serviceMock.viewModel.set(NO_SHIFT_VM);
    createFixture();

    const trigger = fixture.nativeElement.querySelector('.turno-chip') as HTMLElement;
    trigger.click();
    fixture.detectChanges();

    const cta = fixture.nativeElement.querySelector('.turno-cta') as HTMLElement;
    expect(cta).not.toBeNull();
    expect(cta.textContent).toContain('Abrir turno');
  });

  it('shows a loading note while the shift is loading', () => {
    serviceMock.isLoading.set(true);
    createFixture();

    const trigger = fixture.nativeElement.querySelector('.turno-chip') as HTMLElement;
    trigger.click();
    fixture.detectChanges();

    const note = fixture.nativeElement.querySelector('.turno-pop-note') as HTMLElement;
    expect(note).not.toBeNull();
    expect(note.textContent).toContain('Cargando');
  });
});
