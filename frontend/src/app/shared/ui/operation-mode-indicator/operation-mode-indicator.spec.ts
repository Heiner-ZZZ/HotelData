import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';

import { OperationModeIndicatorComponent } from './operation-mode-indicator';
import { OperationModeService, type OperationModeInfo } from '../../../core/services/operation-mode.service';

describe('OperationModeIndicatorComponent', () => {
  let fixture: ComponentFixture<OperationModeIndicatorComponent>;

  const deleteInfo: OperationModeInfo = {
    mode: 'delete',
    label: 'Eliminando',
    description: 'Estás eliminando información.',
    color: 'var(--danger)',
    severity: 3,
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OperationModeIndicatorComponent],
      providers: [
        {
          provide: OperationModeService,
          useValue: {
            mode: signal('delete'),
            info: signal(deleteInfo),
            detail: signal('Reserva BK-42'),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(OperationModeIndicatorComponent);
    fixture.detectChanges();
  });

  it('marks delete mode as critical so it remains legible behind a dark confirmation backdrop', () => {
    const chip: HTMLElement = fixture.nativeElement.querySelector('.op-chip');

    expect(chip.classList.contains('op-chip--delete')).toBe(true);
    expect(chip.getAttribute('aria-label')).toContain('Eliminando');
  });
});
