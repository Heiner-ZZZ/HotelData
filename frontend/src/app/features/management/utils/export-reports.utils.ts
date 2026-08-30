import { ReportsExportService } from '../../../shared/services/reports-export.service';
import {
  buildReportShell,
  buildSummaryGrid,
  buildTable,
} from '../../../shared/utils/report-html-templates';
import type { ManagementReportsViewModel } from '../models/management-reports.model';

type ReportData = ManagementReportsViewModel;

function formatDate(): string {
  return new Date().toISOString().slice(0, 10).replace(/-/g, '');
}

function timestamp(): string {
  return new Date().toLocaleString('es-MX', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  });
}

/**
 * Generates a WeasyPrint-compatible HTML document for the management
 * executive report.
 */
function buildManagementReportHtml(data: ReportData): string {
  const grid = buildSummaryGrid([
    { label: 'Eventos totales', value: String(data.totalEvents), tone: 'neutral' },
    { label: 'Reservas detectadas', value: String(data.reservationsDetected), tone: 'positive' },
    { label: 'Ingresos brutos', value: data.grossRevenueLabel, tone: 'positive' },
    { label: 'Colección fuente', value: data.sourceCollection, tone: 'neutral' },
  ]);

  const hotelTable = data.topHotels.length
    ? buildTable(
        [
          { label: 'Hotel' },
          { label: 'Perfil' },
          { label: 'Eventos', align: 'right' },
          { label: 'Ingresos (USD)', align: 'right' },
        ],
        data.topHotels.map((h) => [h.displayName, h.profileBadge, String(h.events), h.grossRevenueLabel]),
        ['HOTELES LISTADOS', String(data.topHotels.length), `${data.topHotels.reduce((s, h) => s + h.events, 0)}`, '']
      )
    : '';

  const destTable = data.topDestinations.length
    ? buildTable(
        [
          { label: 'Destino' },
          { label: 'Eventos', align: 'right' },
          { label: 'Ingresos (USD)', align: 'right' },
        ],
        data.topDestinations.map((d) => [d.label, String(d.events), d.grossRevenueLabel]),
        ['DESTINOS LISTADOS', String(data.topDestinations.length), `${data.topDestinations.reduce((s, d) => s + d.events, 0)}`, '']
      )
    : '';

  const countryTable = data.topVisitorCountries.length
    ? buildTable(
        [
          { label: 'País' },
          { label: 'Eventos', align: 'right' },
          { label: 'Reservas', align: 'right' },
        ],
        data.topVisitorCountries.map((c) => [c.label, String(c.events), String(c.reservations)]),
        ['PAÍSES LISTADOS', String(data.topVisitorCountries.length), `${data.topVisitorCountries.reduce((s, c) => s + c.events, 0)}`, `${data.topVisitorCountries.reduce((s, c) => s + c.reservations, 0)}`]
      )
    : '';

  const opsTable = data.operationalCounts.length
    ? buildTable(
        [
          { label: 'Colección' },
          { label: 'Valor', align: 'right' },
        ],
        data.operationalCounts.map((o) => [o.label, String(o.value)]),
        ['TOTAL COLECCIONES', String(data.operationalCounts.length), `${data.operationalCounts.reduce((s, o) => s + Number(o.value || 0), 0)}`]
      )
    : '';

  const bodyHtml = `
    ${grid}
    <h2>Top hoteles por revenue</h2>${hotelTable}
    <h2 class="page-break">Top destinos</h2>${destTable}
    <h2>Top países visitantes</h2>${countryTable}
    <h2 class="page-break">Colecciones operativas</h2>${opsTable}
  `;

  return buildReportShell({
    title: 'Reporte Operativo HotelData',
    subtitle: 'Resumen ejecutivo de operación e inteligencia de mercado',
    generatedAt: new Date(),
    metaRows: [
      { label: 'Generado', value: timestamp() },
      { label: 'Colección fuente', value: data.sourceCollection },
    ],
    bodyHtml,
  });
}

/**
 * Backend-delegated Excel export: POSTs structured sheets to
 * `/api/reports/xlsx` (Pandas + OpenPyXL on the backend) and triggers a
 * download in the browser.
 *
 * NOTE: the ReportsExportService is passed in by the caller because
 * `inject()` is only valid inside an Angular injection context (it
 * throws when invoked from a button-click handler).
 */
function parseMoney(label: string | number): number | string {
  if (typeof label === 'number') return label;
  const s = String(label).trim();
  // Extrae número de "$1,234.56" o "1.234,56"
  const cleaned = s.replace(/[^0-9.,-]/g, '').replace(/,/g, '');
  const num = parseFloat(cleaned);
  return isNaN(num) ? s : num;
}

export async function exportToExcel(
  data: ReportData,
  reports: ReportsExportService,
): Promise<void> {
  const filename = `reporte-operativo_${formatDate()}`;
  await reports.exportXlsx({
    filename,
    sheet_title: 'Reporte Operativo HotelData',
    sheets: [
      {
        name: 'Resumen',
        headers: [{ label: 'Métrica' }, { label: 'Valor', align: 'right' }],
        rows: [
          ['Eventos totales', data.totalEvents],
          ['Reservas detectadas', data.reservationsDetected],
          ['Ingresos brutos (USD)', parseMoney(data.grossRevenueLabel)],
          ['Colección fuente', data.sourceCollection],
          ['Generado en', timestamp()],
        ],
        column_widths: { A: 28, B: 30 },
      },
      {
        name: 'Top Hoteles',
        headers: [
          { label: 'Hotel' },
          { label: 'Perfil' },
          { label: 'Eventos', align: 'right' },
          { label: 'Ingresos (USD)', align: 'right' },
        ],
        rows: data.topHotels.map((h) => [h.displayName, h.profileBadge, h.events, parseMoney(h.grossRevenueLabel)]),
        column_widths: { A: 32, B: 28, C: 14, D: 22 },
      },
      {
        name: 'Top Destinos',
        headers: [
          { label: 'Destino' },
          { label: 'Eventos', align: 'right' },
          { label: 'Ingresos (USD)', align: 'right' },
        ],
        rows: data.topDestinations.map((d) => [d.label, d.events, parseMoney(d.grossRevenueLabel)]),
        column_widths: { A: 28, B: 16, C: 22 },
      },
      {
        name: 'Top Países',
        headers: [
          { label: 'País' },
          { label: 'Eventos', align: 'right' },
          { label: 'Reservas', align: 'right' },
        ],
        rows: data.topVisitorCountries.map((c) => [c.label, c.events, c.reservations]),
        column_widths: { A: 28, B: 16, C: 16 },
      },
      {
        name: 'Colecciones',
        headers: [
          { label: 'Colección' },
          { label: 'Valor', align: 'right' },
        ],
        rows: data.operationalCounts.map((o) => [o.label, Number(o.value) || o.value]),
        column_widths: { A: 36, B: 20 },
      },
    ],
  });
}

/**
 * Backend-delegated PDF export: builds an HTML document with full CSS3
 * styling and POSTs it to `/api/reports/pdf` (WeasyPrint).
 */
export async function exportToPdf(
  data: ReportData,
  reports: ReportsExportService,
): Promise<void> {
  const html = buildManagementReportHtml(data);
  await reports.exportPdf(html, `reporte-operativo_${formatDate()}`, 'Reporte Operativo HotelData');
}

/**
 * DOCX export — kept simple. We now generate it from the same report shell
 * with @page rules stripped so Word can render it as a normal document.
 */
export async function exportToDocx(data: ReportData): Promise<void> {
  const html = buildManagementReportHtml(data)
    .replace(/<!DOCTYPE[^>]*>/i, '')
    .replace(/<\/?html[^>]*>/gi, '')
    .replace(/<head>[\s\S]*?<\/head>/i, '')
    .replace(/@page[^}]+}/g, '')
    .replace(/\.report-footer[^}]+}/g, '.report-footer { color: #555; font-size: 9pt; margin-top: 8mm; border-top: 1pt solid #ccc; padding-top: 3mm; }')
    .replace(/PAGE/g, 'page-break-before: always; break-before: page');
  const blob = new Blob([html], { type: 'application/msword' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `reporte-operativo_${formatDate()}.doc`;
  a.click();
  URL.revokeObjectURL(url);
}
