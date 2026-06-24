import {
  Directive,
  ElementRef,
  Input,
  OnInit,
  Renderer2,
  inject,
  OnDestroy
} from '@angular/core';
import { NgControl } from '@angular/forms';
import { Subscription } from 'rxjs';
import { AiSuggestService } from '../services/ai-suggest.service';

@Directive({
  selector: '[appAiSuggest]',
  standalone: true
})
export class AiSuggestDirective implements OnInit, OnDestroy {
  private readonly el = inject(ElementRef);
  private readonly renderer = inject(Renderer2);
  private readonly aiSuggest = inject(AiSuggestService);
  private readonly ngControl = inject(NgControl, { optional: true });

  @Input('appAiSuggest') fieldName!: string;

  private sparkBtn?: HTMLButtonElement;
  private suggestionPill?: HTMLDivElement;
  private wrapper?: HTMLDivElement;
  private sub?: Subscription;

  ngOnInit() {
    const nativeEl = this.el.nativeElement;
    const parent = nativeEl.parentElement;
    if (!parent) return;

    // Create a wrapper to hold the input/textarea and the spark button
    // This avoids modifying the parent's layout (which breaks .field grid layout)
    this.wrapper = this.renderer.createElement('div');
    this.renderer.setAttribute(this.wrapper, 'class', 'ai-input-container');
    this.renderer.setStyle(this.wrapper, 'position', 'relative');
    this.renderer.setStyle(this.wrapper, 'width', '100%');

    // Move the input/textarea into the wrapper
    this.renderer.insertBefore(parent, this.wrapper, nativeEl);
    this.renderer.appendChild(this.wrapper, nativeEl);

    // Add padding to the input so text does not overlap with the spark button
    this.renderer.setStyle(nativeEl, 'padding-right', '2.5rem');

    // Create spark button
    this.sparkBtn = this.renderer.createElement('button');
    this.renderer.setAttribute(this.sparkBtn!, 'type', 'button');
    this.renderer.setAttribute(this.sparkBtn!, 'class', 'btn-ai-spark');
    this.renderer.setAttribute(this.sparkBtn!, 'title', 'Sugerir idea con IA');

    // Create symbol icon
    const icon = this.renderer.createElement('span');
    this.renderer.setAttribute(icon, 'class', 'material-symbols-outlined');
    const iconText = this.renderer.createText('auto_awesome');
    this.renderer.appendChild(icon, iconText);
    this.renderer.appendChild(this.sparkBtn!, icon);

    // Append spark button inside wrapper
    this.renderer.appendChild(this.wrapper, this.sparkBtn!);

    // Listen to button click events
    this.renderer.listen(this.sparkBtn!, 'click', (event: Event) => {
      event.stopPropagation();
      event.preventDefault();
      this.triggerSuggestion();
    });
  }

  private triggerSuggestion() {
    if (this.sparkBtn?.classList.contains('loading')) return;

    const context = this.el.nativeElement.value || '';
    const fName = this.fieldName || this.el.nativeElement.getAttribute('name') || 'campo';

    this.removePill();
    this.renderer.addClass(this.sparkBtn!, 'loading');

    this.sub?.unsubscribe();
    this.sub = this.aiSuggest.getSuggestion(fName, context).subscribe({
      next: (res) => {
        this.renderer.removeClass(this.sparkBtn!, 'loading');
        if (res.ok && res.suggestion) {
          this.showSuggestionPill(res.suggestion);
        }
      },
      error: () => {
        this.renderer.removeClass(this.sparkBtn!, 'loading');
      }
    });
  }

  private showSuggestionPill(suggestion: string) {
    if (!this.wrapper) return;

    // Find the .field container (grandparent of wrapper) to append the pill
    const fieldContainer = this.wrapper.parentElement;
    if (!fieldContainer) return;

    this.suggestionPill = this.renderer.createElement('div');
    this.renderer.setAttribute(this.suggestionPill!, 'class', 'ai-suggestion-pill');

    // Symbol icon
    const spark = this.renderer.createElement('span');
    this.renderer.setAttribute(spark, 'class', 'spark-icon material-symbols-outlined');
    const sparkText = this.renderer.createText('auto_awesome');
    this.renderer.appendChild(spark, sparkText);
    this.renderer.appendChild(this.suggestionPill!, spark);

    // Text label
    const textSpan = this.renderer.createElement('span');
    this.renderer.setAttribute(textSpan, 'class', 'text');
    const labelText = this.renderer.createText('Sugerencia: ');
    const strongText = this.renderer.createElement('strong');
    const sugContent = this.renderer.createText(suggestion);
    this.renderer.appendChild(strongText, sugContent);
    this.renderer.appendChild(textSpan, labelText);
    this.renderer.appendChild(textSpan, strongText);
    this.renderer.appendChild(this.suggestionPill!, textSpan);

    // Apply button badge
    const badge = this.renderer.createElement('span');
    this.renderer.setAttribute(badge, 'class', 'apply-badge');
    const badgeText = this.renderer.createText('Aplicar');
    this.renderer.appendChild(badge, badgeText);
    this.renderer.appendChild(this.suggestionPill!, badge);

    // Append suggestion element inside the field container
    this.renderer.appendChild(fieldContainer, this.suggestionPill!);

    // Handle click to apply
    this.renderer.listen(this.suggestionPill!, 'click', () => {
      this.applySuggestion(suggestion);
    });
  }

  private applySuggestion(suggestion: string) {
    const currentVal = this.el.nativeElement.value || '';
    const newVal = currentVal ? `${currentVal.trim()} ${suggestion}` : suggestion;

    if (this.ngControl && this.ngControl.control) {
      this.ngControl.control.setValue(newVal);
      this.ngControl.control.markAsDirty();
    } else {
      this.el.nativeElement.value = newVal;
      this.el.nativeElement.dispatchEvent(new Event('input', { bubbles: true }));
    }

    this.removePill();
  }

  private removePill() {
    if (this.suggestionPill) {
      this.suggestionPill.remove();
      this.suggestionPill = undefined;
    }
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
    this.removePill();
    // Clean up wrapper - move input back to parent
    if (this.wrapper && this.wrapper.parentElement) {
      const parent = this.wrapper.parentElement;
      const nativeEl = this.el.nativeElement;
      this.renderer.insertBefore(parent, nativeEl, this.wrapper);
      this.renderer.removeChild(parent, this.wrapper);
    }
  }
}
