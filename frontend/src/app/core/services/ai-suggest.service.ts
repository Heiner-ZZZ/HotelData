import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, of } from 'rxjs';
import { API_CONFIG } from '../api/api.config';

export interface AiSuggestionResponse {
  ok: boolean;
  suggestion: string;
  message?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AiSuggestService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getSuggestion(fieldName: string, context: string) {
    return this.http.post<AiSuggestionResponse>(
      `${this.apiConfig.baseUrl}/ai/suggest`,
      {
        field_name: fieldName,
        context: context?.trim() ?? ''
      },
      { withCredentials: true }
    ).pipe(
      catchError(() => of({ ok: false, suggestion: '' }))
    );
  }
}
