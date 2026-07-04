import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { API_CONFIG } from '../../core/api/api.config';

export interface ExcelSheetPayload {
  name: string;
  headers: Array<{ label: string; [style: string]: unknown }>;
  rows: Array<Array<string | number | boolean | null>>;
  column_widths?: Record<string, number>;
  freeze_header?: boolean;
}

export interface ExcelReportPayload {
  filename: string;
  sheet_title?: string;
  sheets: ExcelSheetPayload[];
}

export interface PdfReportPayload {
  html: string;
  filename: string;
  document_title?: string;
}

/**
 * Service that delegates PDF (WeasyPrint) and XLSX (OpenPyXL) generation to
 * the FastAPI backend. Frontend builds the HTML/sheets data, backend
 * converts it server-side. Replaces the old client-side jsPDF + xlsx.
 */
@Injectable({ providedIn: 'root' })
export class ReportsExportService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  /**
   * POSTs an HTML document to /api/reports/pdf and triggers a PDF download.
   * Returns the generated PDF blob for callers who want to use it further.
   */
  async exportPdf(html: string, filename: string, documentTitle?: string): Promise<void> {
    const payload: PdfReportPayload = { html, filename, document_title: documentTitle };
    const blob = await firstValueFrom(
      this.http.post(`${this.apiConfig.baseUrl}/reports/pdf`, payload, {
        responseType: 'blob',
        withCredentials: true,
      })
    );
    this.triggerDownload(blob, `${filename}.pdf`);
  }

  /**
   * POSTs structured sheets to /api/reports/xlsx and triggers an XLSX download.
   */
  async exportXlsx(payload: ExcelReportPayload): Promise<void> {
    const blob = await firstValueFrom(
      this.http.post(`${this.apiConfig.baseUrl}/reports/xlsx`, payload, {
        responseType: 'blob',
        withCredentials: true,
      })
    );
    this.triggerDownload(blob, `${payload.filename}.xlsx`);
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
}
