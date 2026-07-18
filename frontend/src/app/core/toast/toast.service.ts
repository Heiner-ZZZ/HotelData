/**
 * Lightweight toast notification utility.
 *
 * Injects a styled `<div>` into the DOM, animates it in with a spring,
 * and auto-dismisses with a smooth fade-out.  No Angular Material or
 * third-party deps required — vanilla DOM API only, so it works in
 * interceptors and services without needing a ComponentFactoryResolver.
 */

const TOAST_DURATION_MS = 3500;

export type ToastType = 'error' | 'warning' | 'info' | 'success' | 'dark';

interface ToastPalette {
  bg: string;
  icon: string;
  label: string;
}

const PALETTES: Record<ToastType, ToastPalette> = {
  error:   { bg: '#dc3545', icon: '✕',  label: 'Error' },
  warning: { bg: '#f59e0b', icon: '⚠',  label: 'Advertencia' },
  info:    { bg: '#0d6efd', icon: 'ℹ',  label: 'Información' },
  success: { bg: '#16a34a', icon: '✓',  label: 'Éxito' },
  dark:    { bg: '#1e293b', icon: '◉',  label: 'Notificación' },
};

/** Smooth fade-out transition — lasts 400ms with ease-out deceleration. */
function fadeOut(container: HTMLDivElement, onDone: () => void): void {
  // Force a style recalc so the browser picks up the new transition
  container.style.transition = [
    'opacity 400ms cubic-bezier(0.4, 0, 0.2, 1)',
    'transform 400ms cubic-bezier(0.4, 0, 0.2, 1)',
    'box-shadow 400ms cubic-bezier(0.4, 0, 0.2, 1)',
  ].join(', ');
  container.style.opacity = '0';
  container.style.transform = 'translateY(-12px) scale(0.96)';
  container.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
  setTimeout(onDone, 420);
}

/** Shared entrance transition string (applied once at creation). */
const ENTER_TRANSITION = [
  'opacity 340ms cubic-bezier(0.21, 0.69, 0.43, 1)',
  'transform 340ms cubic-bezier(0.21, 0.69, 0.43, 1)',
  'box-shadow 340ms cubic-bezier(0.21, 0.69, 0.43, 1)',
].join(', ');

/**
 * Show a toast notification.
 *
 * @param message  Text to display inside the toast.
 * @param type     Visual style — 'error' (red), 'warning' (amber), 'info' (blue),
 *                 'success' (green), 'dark' (slate).
 * @param duration Milliseconds before auto-dismiss (default 3500).
 */
export function toast(
  message: string,
  type: ToastType = 'info',
  duration: number = TOAST_DURATION_MS,
): void {
  const existing = document.getElementById('hoteldata-toast');
  if (existing) existing.remove();

  const palette = PALETTES[type];
  const textColor = type === 'warning' ? '#1e293b' : '#fff';

  const container = document.createElement('div');
  container.id = 'hoteldata-toast';
  container.innerHTML = `
    <span style="
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; border-radius: 50%;
      background: rgba(255,255,255,0.2);
      font-size: 0.95rem; line-height: 1;
      flex-shrink: 0;
    ">${palette.icon}</span>
    <span style="flex:1; min-width:0;">${message}</span>
  `;

  Object.assign(container.style, {
    position: 'fixed',
    top: '24px',
    right: '24px',
    zIndex: '99999',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '14px 20px',
    borderRadius: '12px',
    background: palette.bg,
    color: textColor,
    fontSize: '0.9375rem',
    fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
    fontWeight: '500',
    lineHeight: '1.4',
    boxShadow: '0 8px 28px rgba(0,0,0,0.16)',
    maxWidth: '420px',
    cursor: 'pointer',
    opacity: '0',
    transform: 'translateY(-16px)',
    transition: ENTER_TRANSITION,
    pointerEvents: 'auto',
  });

  // Click to dismiss → smooth fade-out
  container.addEventListener('click', () => {
    fadeOut(container, () => container.remove());
  });

  document.body.appendChild(container);

  // Trigger entrance animation (next frame so the initial styles apply first)
  requestAnimationFrame(() => {
    container.style.opacity = '1';
    container.style.transform = 'translateY(0)';
  });

  // Auto-dismiss with smooth fade-out
  setTimeout(() => {
    if (document.body.contains(container)) {
      fadeOut(container, () => container.remove());
    }
  }, duration);
}
