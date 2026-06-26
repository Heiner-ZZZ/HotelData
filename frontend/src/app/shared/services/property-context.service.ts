import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class PropertyContextService {
  readonly currentPropId = signal(0);
  readonly currentPropLabel = signal('');
  readonly currentPropLabelShort = signal('');

  setProperty(propId: number, label: string): void {
    this.currentPropId.set(propId);
    this.currentPropLabel.set(label);
    const short = label.length > 18 ? label.slice(0, 16) + '…' : label;
    this.currentPropLabelShort.set(short);
  }

  clear(): void {
    this.currentPropId.set(0);
    this.currentPropLabel.set('');
    this.currentPropLabelShort.set('');
  }
}