import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import type { ManagementReportsViewModel } from '../models/management-reports.model';

type ReportData = ManagementReportsViewModel;

function formatDate(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10).replace(/-/g, '');
}

function timestamp(): string {
  return new Date().toLocaleString('es-MX', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function exportToExcel(data: ReportData): void {
  const wb = XLSX.utils.book_new();

  const summary = [
    ['Métrica', 'Valor'],
    ['Eventos totales', data.totalEvents],
    ['Reservas detectadas', data.reservationsDetected],
    ['Revenue bruto', data.grossRevenueLabel],
    ['Colección fuente', data.sourceCollection],
  ];
  let ws = XLSX.utils.aoa_to_sheet(summary);
  XLSX.utils.book_append_sheet(wb, ws, 'Resumen');

  const hotels = [
    ['Hotel', 'Perfil', 'Eventos', 'Revenue'],
    ...data.topHotels.map((h) => [h.displayName, h.profileBadge, h.events, h.grossRevenueLabel]),
  ];
  ws = XLSX.utils.aoa_to_sheet(hotels);
  XLSX.utils.book_append_sheet(wb, ws, 'Top Hoteles');

  const destinations = [
    ['Destino', 'Eventos', 'Revenue'],
    ...data.topDestinations.map((d) => [d.label, d.events, d.grossRevenueLabel]),
  ];
  ws = XLSX.utils.aoa_to_sheet(destinations);
  XLSX.utils.book_append_sheet(wb, ws, 'Top Destinos');

  const countries = [
    ['País', 'Eventos', 'Reservas'],
    ...data.topVisitorCountries.map((c) => [c.label, c.events, c.reservations]),
  ];
  ws = XLSX.utils.aoa_to_sheet(countries);
  XLSX.utils.book_append_sheet(wb, ws, 'Top Países');

  const ops = [
    ['Colección', 'Valor'],
    ...data.operationalCounts.map((o) => [o.label, o.value]),
  ];
  ws = XLSX.utils.aoa_to_sheet(ops);
  XLSX.utils.book_append_sheet(wb, ws, 'Colecciones');

  const out = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
  triggerDownload(new Blob([out], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }), `reporte-operativo_${formatDate()}.xlsx`);
}

export function exportToPdf(data: ReportData): void {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageW = doc.internal.pageSize.getWidth();

  doc.setFontSize(16);
  doc.text('Reporte Operativo - HotelData', pageW / 2, 18, { align: 'center' });
  doc.setFontSize(9);
  doc.text(`Generado: ${timestamp()}`, pageW / 2, 25, { align: 'center' });

  let y = 32;

  doc.setFontSize(12);
  doc.text('Resumen ejecutivo', 14, y);
  y += 6;
  autoTable(doc, {
    startY: y,
    head: [['Métrica', 'Valor']],
    body: [
      ['Eventos totales', String(data.totalEvents)],
      ['Reservas detectadas', String(data.reservationsDetected)],
      ['Revenue bruto', data.grossRevenueLabel],
      ['Colección fuente', data.sourceCollection],
    ],
    theme: 'grid',
    headStyles: { fillColor: [20, 99, 255] },
    styles: { fontSize: 10 },
  });
  y = (doc as any).lastAutoTable.finalY + 10;

  if (data.topHotels.length) {
    doc.setFontSize(12);
    doc.text('Top hoteles por revenue', 14, y);
    y += 6;
    autoTable(doc, {
      startY: y,
      head: [['Hotel', 'Perfil', 'Eventos', 'Revenue']],
      body: data.topHotels.map((h) => [h.displayName, h.profileBadge, String(h.events), h.grossRevenueLabel]),
      theme: 'grid',
      headStyles: { fillColor: [20, 99, 255] },
      styles: { fontSize: 9 },
    });
    y = (doc as any).lastAutoTable.finalY + 10;
  }

  if (data.topDestinations.length) {
    doc.setFontSize(12);
    doc.text('Top destinos', 14, y);
    y += 6;
    autoTable(doc, {
      startY: y,
      head: [['Destino', 'Eventos', 'Revenue']],
      body: data.topDestinations.map((d) => [d.label, String(d.events), d.grossRevenueLabel]),
      theme: 'grid',
      headStyles: { fillColor: [20, 99, 255] },
      styles: { fontSize: 9 },
    });
    y = (doc as any).lastAutoTable.finalY + 10;
  }

  if (data.topVisitorCountries.length) {
    doc.setFontSize(12);
    doc.text('Top países visitantes', 14, y);
    y += 6;
    autoTable(doc, {
      startY: y,
      head: [['País', 'Eventos', 'Reservas']],
      body: data.topVisitorCountries.map((c) => [c.label, String(c.events), String(c.reservations)]),
      theme: 'grid',
      headStyles: { fillColor: [20, 99, 255] },
      styles: { fontSize: 9 },
    });
    y = (doc as any).lastAutoTable.finalY + 10;
  }

  if (data.operationalCounts.length) {
    doc.setFontSize(12);
    doc.text('Colecciones operativas', 14, y);
    y += 6;
    autoTable(doc, {
      startY: y,
      head: [['Colección', 'Valor']],
      body: data.operationalCounts.map((o) => [o.label, String(o.value)]),
      theme: 'grid',
      headStyles: { fillColor: [20, 99, 255] },
      styles: { fontSize: 9 },
    });
  }

  doc.save(`reporte-operativo_${formatDate()}.pdf`);
}

export function exportToDocx(data: ReportData): void {
  const rows: string[] = [];
  const tr = (...cells: string[]) => `<tr>${cells.map((c) => `<td>${c}</td>`).join('')}</tr>`;
  const th = (...cells: string[]) => `<tr>${cells.map((c) => `<th>${c}</th>`).join('')}</tr>`;

  rows.push(`<h1>Reporte Operativo - HotelData</h1>`);
  rows.push(`<p><em>Generado: ${timestamp()}</em></p>`);

  rows.push(`<h2>Resumen ejecutivo</h2>`);
  rows.push(`<table>${th('Métrica', 'Valor')}${tr('Eventos totales', String(data.totalEvents))}${tr('Reservas detectadas', String(data.reservationsDetected))}${tr('Revenue bruto', data.grossRevenueLabel)}${tr('Colección fuente', data.sourceCollection)}</table>`);

  if (data.topHotels.length) {
    rows.push(`<h2>Top hoteles por revenue</h2>`);
    rows.push(`<table>${th('Hotel', 'Perfil', 'Eventos', 'Revenue')}${data.topHotels.map((h) => tr(h.displayName, h.profileBadge, String(h.events), h.grossRevenueLabel)).join('')}</table>`);
  }

  if (data.topDestinations.length) {
    rows.push(`<h2>Top destinos</h2>`);
    rows.push(`<table>${th('Destino', 'Eventos', 'Revenue')}${data.topDestinations.map((d) => tr(d.label, String(d.events), d.grossRevenueLabel)).join('')}</table>`);
  }

  if (data.topVisitorCountries.length) {
    rows.push(`<h2>Top países visitantes</h2>`);
    rows.push(`<table>${th('País', 'Eventos', 'Reservas')}${data.topVisitorCountries.map((c) => tr(c.label, String(c.events), String(c.reservations))).join('')}</table>`);
  }

  if (data.operationalCounts.length) {
    rows.push(`<h2>Colecciones operativas</h2>`);
    rows.push(`<table>${th('Colección', 'Valor')}${data.operationalCounts.map((o) => tr(o.label, String(o.value))).join('')}</table>`);
  }

  const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 2rem; color: #162033; }
  h1 { color: #1463ff; font-size: 22pt; margin-bottom: 0.2rem; }
  h2 { color: #162033; font-size: 14pt; margin-top: 1.5rem; border-bottom: 2px solid #1463ff; padding-bottom: 0.25rem; }
  table { border-collapse: collapse; width: 100%; margin-top: 0.5rem; }
  th, td { border: 1px solid #d8e0eb; padding: 0.45rem 0.7rem; text-align: left; font-size: 10pt; }
  th { background-color: #1463ff; color: white; font-weight: 600; }
  tr:nth-child(even) td { background-color: #f3f6fb; }
  p em { color: #5f6f87; }
</style>
</head>
<body>
${rows.join('\n')}
</body>
</html>`;

  triggerDownload(new Blob([html], { type: 'application/msword' }), `reporte-operativo_${formatDate()}.doc`);
}
