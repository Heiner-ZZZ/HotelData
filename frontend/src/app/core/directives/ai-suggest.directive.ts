import {
  Directive,
  ElementRef,
  Input,
  inject,
  OnInit,
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
  private readonly aiSuggest = inject(AiSuggestService);
  private readonly ngControl = inject(NgControl, { optional: true });

  @Input('appAiSuggest') fieldName!: string;

  private sparkBtn?: HTMLButtonElement;
  private suggestionPill?: HTMLDivElement;
  private wrapper?: HTMLDivElement;
  private sub?: Subscription;
  private listeners: Array<{ el: HTMLElement; type: string; fn: EventListener }> = [];

  ngOnInit() {
    const nativeEl = this.el.nativeElement;
    const parent = nativeEl.parentElement;
    if (!parent) return;

    // Create a wrapper to hold the input/textarea and the spark button
    this.wrapper = document.createElement('div');
    this.wrapper.setAttribute('class', 'ai-input-container');
    this.wrapper.style.position = 'relative';
    this.wrapper.style.width = '100%';

    // Move the input/textarea into the wrapper
    parent.insertBefore(this.wrapper, nativeEl);
    this.wrapper.appendChild(nativeEl);

    // Add padding to the input so text does not overlap with the spark button
    nativeEl.style.paddingRight = '2.5rem';

    // Create spark button
    this.sparkBtn = document.createElement('button');
    this.sparkBtn.setAttribute('type', 'button');
    this.sparkBtn.setAttribute('class', 'btn-ai-spark');
    this.sparkBtn.setAttribute('title', 'Sugerir idea con IA');

    // Create symbol icon
    const icon = document.createElement('span');
    icon.setAttribute('class', 'material-symbols-outlined');
    const iconText = document.createTextNode('auto_awesome');
    icon.appendChild(iconText);
    this.sparkBtn.appendChild(icon);

    // Append spark button inside wrapper
    this.wrapper.appendChild(this.sparkBtn);

    // Listen to button click events
    const clickHandler = (event: Event) => {
      event.stopPropagation();
      event.preventDefault();
      this.triggerSuggestion();
    };
    this.sparkBtn.addEventListener('click', clickHandler);
    this.listeners.push({ el: this.sparkBtn, type: 'click', fn: clickHandler });
  }

  private triggerSuggestion() {
    if (this.sparkBtn?.classList.contains('loading')) return;

    const context = this.el.nativeElement.value || '';
    const fName = this.fieldName || this.el.nativeElement.getAttribute('name') || 'campo';

    this.removePill();
    this.sparkBtn?.classList.add('loading');

    this.sub?.unsubscribe();
    this.sub = this.aiSuggest.getSuggestion(fName, context).subscribe({
      next: (res) => {
        this.sparkBtn?.classList.remove('loading');
        if (res.ok && res.suggestion) {
          this.showSuggestionPill(res.suggestion);
        }
      },
      error: () => {
        this.sparkBtn?.classList.remove('loading');
      }
    });
  }

  private showSuggestionPill(suggestion: string) {
    if (!this.wrapper) return;

    // Find the .field container (grandparent of wrapper) to append the pill
    const fieldContainer = this.wrapper.parentElement;
    if (!fieldContainer) return;

    this.suggestionPill = document.createElement('div');
    this.suggestionPill.setAttribute('class', 'ai-suggestion-pill');

    // Symbol icon
    const spark = document.createElement('span');
    spark.setAttribute('class', 'spark-icon material-symbols-outlined');
    const sparkText = document.createTextNode('auto_awesome');
    spark.appendChild(sparkText);
    this.suggestionPill.appendChild(spark);

    // Text label
    const textSpan = document.createElement('span');
    textSpan.setAttribute('class', 'text');
    const labelText = document.createTextNode('Sugerencia: ');
    const strongText = document.createElement('strong');
    const sugContent = document.createTextNode(suggestion);
    strongText.appendChild(sugContent);
    textSpan.appendChild(labelText);
    textSpan.appendChild(strongText);
    this.suggestionPill!.appendChild(textSpan);

    // Apply button badge
    const badge = document.createElement('span');
    badge.setAttribute('class', 'apply-badge');
    const badgeText = document.createTextNode('Aplicar');
    badge.appendChild(badgeText);
    this.suggestionPill!.appendChild(badge);

    // Append suggestion element inside the field container
    fieldContainer.appendChild(this.suggestionPill!);

    // Handle click to apply
    const pillClickHandler = () => {
      this.applySuggestion(suggestion);
    };
    this.suggestionPill!.addEventListener('click', pillClickHandler);
    this.listeners.push({ el: this.suggestionPill!, type: 'click', fn: pillClickHandler });
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
    // Clean up event listeners
    for (const { el, type, fn } of this.listeners) {
      el.removeEventListener(type, fn);
    }
    this.listeners = [];
    // Clean up wrapper - move input back to parent
    if (this.wrapper && this.wrapper.parentElement) {
      const parent = this.wrapper.parentElement;
      const nativeEl = this.el.nativeElement;
      parent.insertBefore(nativeEl, this.wrapper);
      parent.removeChild(this.wrapper);
    }
  }
}
