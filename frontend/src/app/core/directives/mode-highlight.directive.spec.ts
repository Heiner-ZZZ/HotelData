import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';

import { OperationModeService } from '../services/operation-mode.service';
import { ModeHighlightDirective } from './mode-highlight.directive';

@Component({
  standalone: true,
  imports: [ModeHighlightDirective],
  template: '<section class="surface-card" appModeHighlight>Panel de form</section>',
})
class HostComponent {}

describe('ModeHighlightDirective', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;

    TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [{ provide: Router, useValue: router }],
    });

    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    const panel = (fixture.nativeElement as HTMLElement).querySelector('section') as HTMLElement;
    return { fixture, panel, mode: TestBed.inject(OperationModeService) };
  }

  it('starts in read mode without the highlight class', () => {
    const { panel, mode } = setup();
    expect(mode.mode()).toBe('read');
    expect(panel.classList.contains('mode-active')).toBe(false);
    // En read el color del chip es el verde de solo lectura.
    expect(panel.style.getPropertyValue('--op-color')).toContain('--success');
  });

  it('adds mode-active with the amber color while creating (insert)', () => {
    const { fixture, panel, mode } = setup();
    mode.setMode('insert', 'Nueva promoción');
    fixture.detectChanges();

    expect(panel.classList.contains('mode-active')).toBe(true);
    expect(panel.style.getPropertyValue('--op-color')).toContain('--warning');
  });

  it('keeps the highlight with the update color while editing', () => {
    const { fixture, panel, mode } = setup();
    mode.setMode('update', 'Verano');
    fixture.detectChanges();

    expect(panel.classList.contains('mode-active')).toBe(true);
    // El color de update mezcla warning+danger (naranja del mode-indicator).
    expect(panel.style.getPropertyValue('--op-color')).toContain('--danger');
  });

  it('removes the highlight when returning to read mode', () => {
    const { fixture, panel, mode } = setup();
    mode.setMode('insert', 'x');
    fixture.detectChanges();
    expect(panel.classList.contains('mode-active')).toBe(true);

    mode.setMode('read');
    fixture.detectChanges();
    expect(panel.classList.contains('mode-active')).toBe(false);
  });
});
