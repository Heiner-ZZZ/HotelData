/**
 * Cliente-side CSV export helper.
 *
 * Genera un archivo CSV con BOM UTF-8 (para que Excel/Google Sheets abran
 * correctamente los acentos) y escapado RFC 4180 de comas, comillas y saltos
 * de línea. Reutilizado por los dashboards simples (R2.2, I1.1) y cualquier
 * grilla que necesite exportación sin depender del backend.
 */

export function csvEscape(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined) return '';
  const s = String(value);
  if (/[",\n\r]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

/**
 * Descarga `rows` como un archivo CSV con encabezados.
 *
 * @param filename Nombre del archivo sin extensión (se le agrega `.csv`).
 * @param headers  Encabezados de columnas.
 * @param rows     Filas de datos (se escapan automáticamente).
 */
export function exportCsv(
  filename: string,
  headers: (string | number)[],
  rows: (string | number | boolean | null | undefined)[][],
): void {
  const lines = [
    headers.map((h) => csvEscape(h)).join(','),
    ...rows.map((r) => r.map((cell) => csvEscape(cell)).join(',')),
  ];
  const bom = '\uFEFF';
  const blob = new Blob([bom + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
