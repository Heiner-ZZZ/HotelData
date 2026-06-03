import { Injectable, signal } from '@angular/core';

const STORAGE_KEY = 'hoteldata-theme';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  readonly isDark = signal(false);

  constructor() {
    const stored = localStorage.getItem(STORAGE_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const dark = stored === 'dark' || (stored === null && prefersDark);
    this.apply(dark);
  }

  toggle() {
    this.apply(!this.isDark());
  }

  private apply(dark: boolean) {
    this.isDark.set(dark);
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light');
  }
}
