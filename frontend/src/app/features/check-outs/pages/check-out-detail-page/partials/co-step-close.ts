import { FormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-co-step-close',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="co-card co-step-card">
      <div class="co-step-badge">Paso 5</div>
      <h2 class="co-step-title">Cerrar estancia</h2>

      <p class="co-close-desc">Al cerrar el check-out, el sistema realizar&aacute; autom&aacute;ticamente:</p>
      <div class="co-auto-list">
        <div class="co-auto-item"><span class="material-symbols-outlined">check_circle</span> Cambiar habitaci&oacute;n <strong>Occupied &rarr; Dirty</strong></div>
        <div class="co-auto-item"><span class="material-symbols-outlined">check_circle</span> Crear tarea: <strong>Limpiar {{ roomLabel() }}</strong></div>
        <div class="co-auto-item"><span class="material-symbols-outlined">check_circle</span> Liberar inventario de habitaciones</div>
        <div class="co-auto-item"><span class="material-symbols-outlined">check_circle</span> Registrar hora real y usuario</div>
        <div class="co-auto-item"><span class="material-symbols-outlined">check_circle</span> Actualizar dashboard de recepci&oacute;n</div>
        <div class="co-auto-item"><span class="material-symbols-outlined">check_circle</span> Auditor&iacute;a completa con IP y m&eacute;todo</div>
      </div>

      <div class="co-close-checks">
        <label class="co-check" [class.co-checked]="roomInspected()">
          <input type="checkbox" [ngModel]="roomInspected()" (ngModelChange)="roomInspectedChange.emit($event)" />
          <span>Habitaci&oacute;n y minibar revisados</span>
          @if (roomInspected()) { <span class="co-check-icon">&check;</span> }
        </label>
        <label class="co-check" [class.co-checked]="keysReturned()">
          <input type="checkbox" [ngModel]="keysReturned()" (ngModelChange)="keysReturnedChange.emit($event)" />
          <span>Llaves devueltas</span>
          @if (keysReturned()) { <span class="co-check-icon">&check;</span> }
        </label>
      </div>

      <div class="co-damage-row">
        <span class="co-label">&iquest;Da&ntilde;os en la habitaci&oacute;n?</span>
        <div class="co-damage-toggle">
          <button class="co-dmg-btn" [class.active]="!damagesFound()" (click)="damagesFoundChange.emit(false)">No</button>
          <button class="co-dmg-btn co-dmg-danger" [class.active]="damagesFound()" (click)="damagesFoundChange.emit(true)">S&iacute;</button>
        </div>
      </div>

      <textarea class="co-textarea" rows="2"
        [ngModel]="observations()" (ngModelChange)="observationsChange.emit($event)"
        placeholder="Observaciones de salida..."></textarea>

      @if (completeError()) { <div class="toast toast-error">{{ completeError() }}</div> }

      <div class="co-step-actions">
        <button class="co-btn-outline" (click)="prev.emit()">&larr; Atr&aacute;s</button>
        <button class="co-cta" (click)="complete.emit()" [disabled]="completing()">
          @if (completing()) {
            <span class="material-symbols-outlined spinning">sync</span> Procesando...
          } @else {
            <span class="material-symbols-outlined">logout</span> Cerrar estancia &amp; Check-Out
          }
        </button>
      </div>
    </section>
  `
})
export class CoStepCloseComponent {
  readonly roomLabel = input('');
  readonly roomInspected = input(false);
  readonly keysReturned = input(false);
  readonly damagesFound = input(false);
  readonly observations = input('');
  readonly completing = input(false);
  readonly completeError = input('');

  readonly roomInspectedChange = output<boolean>();
  readonly keysReturnedChange = output<boolean>();
  readonly damagesFoundChange = output<boolean>();
  readonly observationsChange = output<string>();
  readonly prev = output<void>();
  readonly complete = output<void>();
}
