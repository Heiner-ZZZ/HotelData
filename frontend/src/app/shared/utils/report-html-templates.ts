/**
 * Shared HTML5/CSS3 template builder for WeasyPrint PDF generation.
 *
 * Provides a single source of truth for branded headers, executive summary
 * cards, financial tables, and page footers — used by every report PDF in
 * the system (ledger, audit log, property history, management reports,
 * reputation dashboard).
 *
 * Bring your own body HTML; the wrapper handles branding, paper size,
 * page breaks, and footer signatures.
 */

const SHARED_STYLES = `
  @page { size: A4; margin: 16mm 14mm 18mm 14mm; }
  @page :first { margin-top: 0; }

  :root {
    --c-primary: #1e3c78;
    --c-primary-light: #2d78dc;
    --c-success: #166534;
    --c-success-bg: #f0fdf4;
    --c-danger: #991b1b;
    --c-danger-bg: #fef2f2;
    --c-warning: #92400e;
    --c-warning-bg: #fff7ed;
    --c-text: #0f172a;
    --c-text-muted: #64748b;
    --c-border: #d8e0eb;
    --c-bg-soft: #f8fafc;
  }

  * { box-sizing: border-box; }

  body {
    font-family: 'DejaVu Sans', 'Segoe UI', Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.4;
    color: var(--c-text);
    margin: 0;
    padding: 0;
  }

  /* ─── Branded report header ─── */
  .report-header {
    background: linear-gradient(135deg, #1e3c78 0%, #2d78dc 100%);
    color: #fff;
    padding: 18mm 14mm 8mm;
    margin: 0 -14mm 0 -14mm;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  .report-header .brand {
    font-size: 22pt;
    font-weight: 700;
    letter-spacing: -0.01em;
    line-height: 1;
  }
  .report-header .tagline {
    font-size: 8.5pt;
    color: #c8d7f0;
    margin-top: 2mm;
  }
  .report-header .title-block { text-align: right; }
  .report-header .title-block .title {
    font-size: 16pt;
    font-weight: 700;
  }
  .report-header .title-block .subtitle {
    font-size: 8.5pt;
    color: #c8d7f0;
    margin-top: 1mm;
  }
  .accent-bar {
    height: 2mm;
    background: linear-gradient(90deg, #1e3c78, #2d78dc);
    margin: 0 -14mm 6mm;
  }

  /* ─── Page footer ─── */
  .report-footer {
    position: fixed;
    bottom: -10mm;
    left: 0; right: 0;
    padding: 2mm 14mm;
    border-top: 0.5pt solid var(--c-border);
    color: var(--c-text-muted);
    font-size: 7.5pt;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  /* ─── Generic blocks ─── */
  .meta-bar {
    background: var(--c-bg-soft);
    border: 0.5pt solid var(--c-border);
    border-radius: 4pt;
    padding: 5mm 6mm;
    margin-bottom: 5mm;
    font-size: 9pt;
  }
  .meta-bar .meta-label {
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 7.5pt;
    color: var(--c-text-muted);
    margin-bottom: 2mm;
  }
  .meta-bar .meta-row { display: flex; gap: 4mm; flex-wrap: wrap; }

  h1 { font-size: 18pt; margin: 0 0 4mm; color: var(--c-primary); }
  h2 {
    font-size: 13pt;
    color: var(--c-primary);
    margin: 7mm 0 3mm;
    padding-bottom: 2mm;
    border-bottom: 1pt solid var(--c-border);
  }
  h3 { font-size: 11pt; margin: 4mm 0 2mm; color: var(--c-text); }

  p { margin: 0 0 2mm; }

  /* ─── Summary card grid ─── */
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(50mm, 1fr));
    gap: 3mm;
    margin-bottom: 5mm;
  }
  .summary-card {
    background: var(--c-bg-soft);
    border: 0.5pt solid var(--c-border);
    border-radius: 4pt;
    padding: 4mm 5mm;
  }
  .summary-card .label {
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--c-text-muted);
  }
  .summary-card .value {
    font-size: 13pt;
    font-weight: 700;
    color: var(--c-text);
    margin-top: 1mm;
  }
  .summary-card .sub {
    font-size: 8pt;
    color: var(--c-text-muted);
    margin-top: 0.5mm;
  }
  .summary-card.is-positive { background: var(--c-success-bg); border-color: var(--c-success); }
  .summary-card.is-positive .value { color: var(--c-success); }
  .summary-card.is-negative { background: var(--c-danger-bg); border-color: var(--c-danger); }
  .summary-card.is-negative .value { color: var(--c-danger); }
  .summary-card.is-warning { background: var(--c-warning-bg); border-color: var(--c-warning); }
  .summary-card.is-warning .value { color: var(--c-warning); }

  /* ─── Tables ─── */
  table.financial {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 5mm;
    font-size: 9pt;
  }
  table.financial thead {
    background: var(--c-primary);
    color: #fff;
    font-weight: 700;
  }
  table.financial thead th {
    padding: 3mm 4mm;
    text-align: left;
    border: 0;
    font-size: 9pt;
  }
  table.financial tbody td {
    padding: 2.5mm 4mm;
    border-bottom: 0.4pt solid var(--c-border);
  }
  table.financial tbody tr:nth-child(even) td { background: var(--c-bg-soft); }
  table.financial .num { text-align: right; font-variant-numeric: tabular-nums; }
  table.financial .positive { color: var(--c-success); font-weight: 600; }
  table.financial .negative { color: var(--c-danger); font-weight: 600; }
  table.financial tfoot td {
    padding: 3mm 4mm;
    background: #e8f5e9;
    font-weight: 700;
    border-top: 1pt solid var(--c-primary);
  }
  table.financial tfoot.danger td { background: var(--c-danger-bg); color: var(--c-danger); }
  table.financial tfoot.subtle td { background: #eef2ff; color: var(--c-primary); }
  table.financial .section-header {
    background: var(--c-primary-light);
    color: #fff;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 8.5pt;
  }
  table.financial .section-header td { padding: 2.5mm 4mm; }
  table.financial .empty-row td { text-align: center; color: var(--c-text-muted); font-style: italic; }

  /* ─── Badges / tags ─── */
  .badge {
    display: inline-block;
    padding: 1pt 6pt;
    border-radius: 3pt;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: var(--c-border);
    color: var(--c-text);
  }
  .badge.success { background: var(--c-success-bg); color: var(--c-success); }
  .badge.danger  { background: var(--c-danger-bg); color: var(--c-danger); }
  .badge.warning { background: var(--c-warning-bg); color: var(--c-warning); }
  .badge.info    { background: #e0f2fe; color: #075985; }

  /* ─── Two-column body for P&L / Balance ─── */
  .two-col { display: flex; gap: 6mm; }
  .two-col > * { flex: 1; min-width: 0; }

  /* ─── Page break helpers ─── */
  .page-break { page-break-before: always; break-before: page; }
  .no-break   { page-break-inside: avoid; break-inside: avoid; }

  /* ─── Dev/equal-party ─── */
  .eq-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--c-bg-soft);
    border-top: 1pt solid var(--c-primary);
    padding: 4mm 5mm;
    font-weight: 700;
    border-radius: 0 0 4pt 4pt;
    margin-bottom: 3mm;
  }
  .eq-bar.success { background: var(--c-success-bg); border-color: var(--c-success); }
  .eq-bar.danger  { background: var(--c-danger-bg); border-color: var(--c-danger); }
  .eq-bar .label { font-size: 10pt; }
  .eq-bar .value { font-size: 13pt; font-variant-numeric: tabular-nums; }
`;

export interface StandardReportShellInput {
  title: string;
  subtitle?: string;
  generatedAt?: Date;
  metaRows?: Array<{ label: string; value: string }>;
  bodyHtml: string;
}

const fmtDate = (d: Date): string =>
  d.toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' });

const fmtTime = (d: Date): string =>
  d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });

/**
 * Wrap a report body in the standard branded shell with header, accent
 * bar, page footer, and an optional meta-block under the header.
 */
export function buildReportShell(input: StandardReportShellInput): string {
  const now = input.generatedAt ?? new Date();
  const metaRows = input.metaRows ?? [];
  const metaHtml = metaRows.length
    ? `<div class="meta-bar"><div class="meta-label">Información del reporte</div>` +
      `<div class="meta-row">` +
      metaRows
        .map(
          (r) =>
            `<div><strong>${esc(r.label)}:</strong> ${esc(r.value)}</div>`
        )
        .join('') +
      `</div></div>`
    : '';

  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>${esc(input.title)}</title>
<style>${SHARED_STYLES}</style>
</head>
<body>
  <header class="report-header">
    <div>
      <div class="brand">HotelData</div>
      <div class="tagline">Sistema de Gestión Hotelera</div>
    </div>
    <div class="title-block">
      <div class="title">${esc(input.title)}</div>
      ${input.subtitle ? `<div class="subtitle">${esc(input.subtitle)}</div>` : ''}
    </div>
  </header>
  <div class="accent-bar"></div>
  ${metaHtml}
  <main>${input.bodyHtml}</main>
  <footer class="report-footer">
    <span>CONFIDENCIAL — HotelData</span>
    <span>Generado: ${esc(fmtDate(now))} ${esc(fmtTime(now))}</span>
  </footer>
</body>
</html>`;
}

export function esc(v: unknown): string {
  if (v === null || v === undefined) return '';
  const s = String(v);
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function fmtUsd(n: number, opts: { showZero?: boolean } = {}): string {
  if (!isFinite(n)) return '—';
  if (n === 0 && !opts.showZero) return '—';
  const sign = n < 0 ? '-' : '';
  return sign + '$' + Math.abs(n).toFixed(2);
}

export function fmtNumber(n: number): string {
  if (!isFinite(n)) return '—';
  return String(n);
}

export interface SummaryCardInput {
  label: string;
  value: string;
  sub?: string;
  tone?: 'positive' | 'negative' | 'warning' | 'neutral';
}

export function buildSummaryGrid(cards: SummaryCardInput[]): string {
  const items = cards
    .map((c) => {
      const toneClass = c.tone && c.tone !== 'neutral' ? ` is-${c.tone}` : '';
      const sub = c.sub ? `<div class="sub">${esc(c.sub)}</div>` : '';
      return `<div class="summary-card${toneClass}">
        <div class="label">${esc(c.label)}</div>
        <div class="value">${esc(c.value)}</div>
        ${sub}
      </div>`;
    })
    .join('');
  return `<div class="summary-grid">${items}</div>`;
}

export interface TableColumn {
  label: string;
  align?: 'left' | 'right' | 'center';
  numberFormat?: string;
  cssClass?: string;
}

/**
 * Build a styled financial table from headers + 2D rows. Returns HTML
 * with thead/tbody for a single sheet; tfoot optional.
 */
export function buildTable(
  columns: TableColumn[],
  rows: Array<Array<string | number>>,
  footerRow?: Array<string | number>
): string {
  const thead = columns
    .map((c) => {
      const align = c.align === 'right' ? 'right' : c.align === 'center' ? 'center' : 'left';
      return `<th style="text-align:${align}">${esc(c.label)}</th>`;
    })
    .join('');
  const tbody =
    rows.length === 0
      ? `<tr class="empty-row"><td colspan="${columns.length}">Sin datos para los filtros aplicados</td></tr>`
      : rows
          .map((row) => {
            const cells = row
              .map((cell, idx) => {
                const col = columns[idx] ?? {};
                const align = col.align === 'right' ? 'right' : col.align === 'center' ? 'center' : 'left';
                const cls = col.cssClass ? ` class="${col.cssClass}"` : '';
                return `<td style="text-align:${align}"${cls}>${esc(cell)}</td>`;
              })
              .join('');
            return `<tr>${cells}</tr>`;
          })
          .join('');

  const tfoot = footerRow
    ? `<tfoot><tr>${footerRow
        .map((cell, idx) => {
          const col = columns[idx] ?? {};
          const align = col.align === 'right' ? 'right' : col.align === 'center' ? 'center' : 'left';
          return `<td style="text-align:${align}">${esc(cell)}</td>`;
        })
        .join('')}</tr></tfoot>`
    : '';
  return `<table class="financial">
    <thead><tr>${thead}</tr></thead>
    <tbody>${tbody}</tbody>
    ${tfoot}
  </table>`;
}
