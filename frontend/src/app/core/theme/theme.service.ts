import { Injectable, signal } from '@angular/core';

const STORAGE_KEY = 'hoteldata-theme';
const PREFERENCE_KEY = 'hoteldata-theme-preference';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  readonly isDark = signal(false);

  constructor() {
    const preference = localStorage.getItem(PREFERENCE_KEY);
    const stored = localStorage.getItem(STORAGE_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    let dark: boolean;
    if (preference === 'system') {
      dark = prefersDark;
    } else if (preference === 'light') {
      dark = false;
    } else if (preference === 'dark') {
      dark = true;
    } else {
      dark = stored === 'dark' || (stored === null && prefersDark);
    }

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
