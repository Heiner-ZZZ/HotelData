import type { ColDef } from 'ag-grid-community';

export interface ColumnActionCallbacks {
  onConfirm: (bookingId: string, guestName: string) => void;
  onReject: (bookingId: string, guestName: string) => void;
  isStaff: () => boolean;
}

export function buildColumnDefs(
  callbacks: ColumnActionCallbacks
): ColDef[] {
  return [
    {
      field: 'folio',
      headerName: 'Folio',
      width: 120,
      cellRenderer: (p: any) => {
        if (p.value) {
          const c = document.createElement('code');
          c.className = 'folio-tag';
          c.textContent = p.value;
          return c;
        }
        const s = document.createElement('span');
        s.className = 'folio-pending';
        s.textContent = '—';
        return s;
      },
    },
    {
      field: 'bookingId',
      headerName: 'Reserva',
      minWidth: 180,
      cellRenderer: (p: any) => {
        const wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;flex-direction:column;gap:1px';
        const code = document.createElement('code');
        code.style.cssText = 'font-size:0.72rem;font-weight:600;color:var(--accent)';
        code.textContent = p.value;
        const hotel = document.createElement('span');
        hotel.style.cssText = 'font-size:0.68rem;color:var(--muted-text)';
        hotel.textContent = p.data?.hotelLabel || '';
        wrap.appendChild(code);
        wrap.appendChild(hotel);
        return wrap;
      },
    },
    {
      field: 'guestName',
      headerName: 'Huésped',
      minWidth: 150,
      flex: 1,
      cellRenderer: (p: any) => {
        const wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;flex-direction:column;gap:1px;overflow:hidden;min-width:0';
        const name = document.createElement('span');
        name.style.cssText = 'font-size:0.82rem;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis';
        name.textContent = p.value;
        wrap.appendChild(name);
        const email = document.createElement('span');
        email.style.cssText = 'font-size:0.68rem;color:var(--muted-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis';
        email.textContent = p.data?.guestEmail || '';
        wrap.appendChild(email);
        return wrap;
      },
    },
    {
      field: 'checkInDate',
      headerName: 'Check-in \u2192 Check-out',
      minWidth: 300,
      cellRenderer: (p: any) => {
        const wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;align-items:center;gap:0.3rem;font-size:0.78rem;white-space:nowrap';

        const ci = document.createElement('span');
        ci.textContent = p.value || '';
        if (p.data?.checkInTimeActual) {
          const ciTime = document.createElement('span');
          ciTime.style.cssText = 'font-size:0.62rem;font-weight:600;color:#6b7280;margin-left:3px';
          ciTime.textContent = p.data.checkInTimeActual;
          ci.appendChild(ciTime);
        }

        const arrow = document.createElement('span');
        arrow.style.cssText = 'color:var(--muted-text);font-size:0.7rem';
        arrow.textContent = '\u2192';

        const co = document.createElement('span');
        co.textContent = p.data?.checkOutDate || '';
        if (p.data?.checkOutTimeActual) {
          const coTime = document.createElement('span');
          coTime.style.cssText = 'font-size:0.62rem;font-weight:600;color:#6b7280;margin-left:3px';
          coTime.textContent = p.data.checkOutTimeActual;
          co.appendChild(coTime);
        }

        const nights = document.createElement('span');
        nights.style.cssText = 'display:inline-flex;align-items:center;gap:2px;font-size:0.65rem;font-weight:600;color:#374151;padding:0.1rem 0.35rem;border-radius:3px;white-space:nowrap';
        const moonIcon = document.createElement('span');
        moonIcon.className = 'material-symbols-outlined';
        moonIcon.style.cssText = 'font-size:0.75rem;--icon-FILL:1;--icon-opsz:14;color:#1e3a5f';
        moonIcon.textContent = 'nightlight';
        const nightsNum = document.createElement('span');
        nightsNum.textContent = String(p.data?.totalNights || 0);
        nights.append(moonIcon, nightsNum);

        wrap.append(ci, arrow, co, nights);
        return wrap;
      },
    },
    {
      field: 'stayStatus',
      headerName: 'Estadía',
      width: 150,
      cellRenderer: (p: any) => {
        const wrap = document.createElement('span');
        wrap.style.cssText = 'display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;font-weight:600;white-space:nowrap';
        const icon = document.createElement('span');
        icon.className = 'material-symbols-outlined';
        icon.style.cssText = 'font-size:0.85rem';
        let iconName = '';
        let label = '';
        /** Chip "Reabrible" del marcador de no-show (solo ventana abierta). */
        let chip: HTMLSpanElement | null = null;
        /** Reabierta tras no-show: el gerente la reabrió porque el huésped llegó
         * después del no-show. MISMO criterio de ventana que el banner
         * ``reopenedNotice`` del detalle de check-in (vía ``reopenWindow``
         * server-authoritative): solo se marca dentro de la ventana abierta. */
        const reopened = !!p.data?.noShowReopenedAt && p.data?.reopenWindow === 'open';
        if (p.value === 'checked_in') {
          iconName = 'check_circle';
          label = 'Check-in';
          wrap.style.color = '#2563eb';
          if (reopened) {
            wrap.title = 'Reabierta tras no-show: el huésped llegó después del no-show (ventana abierta)';
          }
        } else if (p.value === 'checked_out') {
          iconName = 'logout';
          label = 'Check-out';
          wrap.style.color = '#7c3aed';
        } else if (p.value === 'pending') {
          iconName = reopened ? 'replay' : 'schedule';
          label = 'Pendiente';
          wrap.style.color = '#6b7280';
          if (reopened) {
            wrap.title = 'Reabierta tras no-show: el huésped llegó después del no-show (ventana abierta) — registralo como check-in de llegada tardía';
          }
        } else if (p.value === 'no_show') {
          // Marcador de no-show — MISMO criterio de ventana que el calendario
          // de Recepción (server-authoritative vía ``reopenWindow``):
          // 'open' → reabrible (hoy/ayer con estadía vigente): ámbar + chip;
          // 'too_late'/'stay_ended' → ventana cerrada: rojo sin chip, para no
          // invitar a una reapertura que la API rechazaría.
          const window = p.data?.reopenWindow;
          const reopenable = window === 'open';
          iconName = 'event_busy';
          label = 'No-show';
          wrap.style.color = reopenable ? '#b45309' : '#b91c1c';
          wrap.title = reopenable
            ? 'No-show: reabrible dentro de la ventana (hoy o ayer con estadía vigente)'
            : window === 'too_late'
              ? 'No-show: ventana de reapertura cerrada (check-in con más de un día de retraso)'
              : window === 'stay_ended'
                ? 'No-show: la estadía ya terminó y la ventana de reapertura cerró'
                : 'No-show: el huésped no llegó';
          if (reopenable) {
            chip = document.createElement('span');
            chip.style.cssText = 'font-size:0.58rem;font-weight:700;letter-spacing:0.02em;padding:0.08rem 0.3rem;border-radius:999px;background:color-mix(in srgb, var(--warning) 16%, transparent);color:var(--warning);white-space:nowrap';
            chip.textContent = 'Reabrible';
          }
        } else {
          label = p.value || '';
          wrap.style.color = '#374151';
        }
        // Marca de reapertura: chip púrpura (distinto del ámbar "Reabrible" del
        // no-show activo) sobre cualquier estado no-no-show con la marca vigente.
        if (reopened && p.value !== 'no_show') {
          chip = document.createElement('span');
          chip.style.cssText = 'font-size:0.58rem;font-weight:700;letter-spacing:0.02em;padding:0.08rem 0.3rem;border-radius:999px;background:color-mix(in srgb, var(--purple) 16%, transparent);color:var(--purple);white-space:nowrap';
          chip.textContent = 'Reabierta';
        }
        icon.textContent = iconName;
        if (iconName) wrap.appendChild(icon);
        const txt = document.createElement('span');
        txt.textContent = label;
        wrap.appendChild(txt);
        if (chip) wrap.appendChild(chip);
        return wrap;
      },
    },
    {
      field: 'bookingSource',
      headerName: 'Fuente',
      width: 100,
      cellRenderer: (p: any) => {
        const tag = document.createElement('span');
        tag.style.cssText = 'font-size:0.62rem;font-weight:600;text-transform:uppercase;letter-spacing:0.03em;color:var(--muted-text);padding:0.15rem 0.35rem;border-radius:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:inline-block;max-width:80px';
        tag.textContent = p.value || '\u2014';
        return tag;
      },
    },
    {
      field: 'totalPrice',
      headerName: 'Total',
      width: 90,
      type: 'numericColumn',
      cellRenderer: (p: any) => {
        if (p.value != null) {
          const wrap = document.createElement('span');
          const num = document.createElement('span');
          num.style.cssText = 'font-weight:600;font-variant-numeric:tabular-nums';
          num.textContent = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(p.value);
          const cur = document.createElement('span');
          cur.style.cssText = 'font-size:0.62rem;color:var(--muted-text);font-weight:500;margin-left:2px';
          cur.textContent = p.data?.currency || '';
          wrap.append(num, cur);
          return wrap;
        }
        const na = document.createElement('span');
        na.style.cssText = 'color:var(--muted-text);opacity:0.4';
        na.textContent = '\u2014';
        return na;
      },
    },
    {
      field: 'status',
      headerName: 'Estado',
      width: 120,
      cellRenderer: (p: any) => {
        const badge = document.createElement('span');
        badge.style.cssText = 'font-size:0.7rem;font-weight:600;padding:0.2rem 0.5rem;border-radius:99px;white-space:nowrap';
        const s = p.value || '';
        if (s === 'pending') {
          badge.style.cssText += 'background:#fef3c7;color:#92400e';
          badge.textContent = 'Pendiente';
        } else if (s === 'confirmed') {
          badge.style.cssText += 'background:#dcfce7;color:#166534';
          badge.textContent = 'Confirmada';
        } else if (s === 'checked_in') {
          badge.style.cssText += 'background:#dbeafe;color:#1e40af';
          badge.textContent = 'Check-in';
        } else if (s === 'checked_out') {
          badge.style.cssText += 'background:#f3e8ff;color:#6b21a8';
          badge.textContent = 'Check-out';
        } else {
          badge.style.cssText += 'background:#f3f4f6;color:#6b7280';
          badge.textContent = s;
        }
        return badge;
      },
    },
    {
      headerName: '',
      // Ancho suficiente para dos botones de 2rem + gap 8px + padding de celda,
      // para que Confirmar/Rechazar no se peguen (queja de UX en la recepción).
      width: 96,
      sortable: false,
      filter: false,
      resizable: false,
      cellRenderer: (p: any) => {
        if (p.data?.status !== 'pending' || !callbacks.isStaff()) return '';
        const wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;align-items:center;gap:8px;justify-content:flex-end';

        /** Botón de icono con nombre accesible (aria-label) y hover visible.
         *  Estilos inline: los SCSS del componente no alcanzan las celdas
         *  dinámicas de AG Grid (encapsulación), así que el feedback de hover
         *  se maneja por listener, no por clase CSS. */
        const buildAction = (
          iconName: string,
          label: string,
          hoverColor: string,
          onClick: () => void
        ): HTMLButtonElement => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.style.cssText = `width:2rem;height:2rem;display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--app-border);border-radius:6px;background:transparent;color:var(--muted-text);cursor:pointer;transition:background 120ms,border-color 120ms,color 120ms`;
          btn.setAttribute('aria-label', label);
          btn.title = label;
          const icon = document.createElement('span');
          icon.className = 'material-symbols-outlined';
          icon.style.cssText = 'font-size:1.15rem';
          icon.textContent = iconName;
          btn.appendChild(icon);
          btn.addEventListener('mouseenter', () => {
            btn.style.color = hoverColor;
            btn.style.borderColor = hoverColor;
            btn.style.background = `color-mix(in srgb, ${hoverColor} 7%, transparent)`;
          });
          btn.addEventListener('mouseleave', () => {
            btn.style.color = 'var(--muted-text)';
            btn.style.borderColor = 'var(--app-border)';
            btn.style.background = 'transparent';
          });
          btn.addEventListener('click', (e: Event) => {
            e.stopPropagation();
            onClick();
          });
          return btn;
        };

        const confirm = buildAction('check_circle', 'Confirmar reserva', 'var(--success)', () =>
          callbacks.onConfirm(p.data.bookingId, p.data.guestName)
        );
        const reject = buildAction('cancel', 'Rechazar reserva', 'var(--danger)', () =>
          callbacks.onReject(p.data.bookingId, p.data.guestName)
        );

        wrap.append(confirm, reject);
        return wrap;
      },
    },
  ];
}
