import { Directive, ElementRef, HostListener, inject } from '@angular/core';
import { NgControl } from '@angular/forms';

/**
 * Attribute directive for <input type="text" inputmode="decimal"> fields.
 *
 * On blur:  formats the value to 2 decimal places  (e.g., "25" → "25.00")
 * On focus: reverts to a raw number string for easy editing (e.g., "25.00" → "25")
 *
 * Supports European comma decimals ("25,00") by normalising to dot on blur.
 *
 * @example
 * <input type="text" inputmode="decimal" appAmountInput formControlName="price" />
 */
@Directive({
  selector: '[appAmountInput]',
  standalone: true,
})
export class AmountInputDirective {
  private readonly el = inject<ElementRef<HTMLInputElement>>(ElementRef);
  private readonly control = inject(NgControl, { optional: true });

  @HostListener('blur')
  onBlur(): void {
    const raw = this.el.nativeElement.value;
    if (raw === '' || raw == null) return;
    // Normalise comma decimal separators
    const normalised = raw.replace(',', '.');
    const num = Number(normalised);
    if (isNaN(num)) return;
    const formatted = num.toFixed(2);
    this._updateValue(formatted);
  }

  @HostListener('focus')
  onFocus(): void {
    const raw = this.el.nativeElement.value;
    if (raw === '' || raw == null) return;
    const num = parseFloat(raw.replace(',', '.'));
    if (isNaN(num)) return;
    // Show raw number without trailing zeros for easy editing
    this._updateValue(String(num));
  }

  private _updateValue(value: string): void {
    if (this.control?.control) {
      this.control.control.setValue(value as any, { emitEvent: false });
    }
    this.el.nativeElement.value = value;
  }
}
