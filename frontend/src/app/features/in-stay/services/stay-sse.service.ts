import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface StayNotification {
  type: 'new_message' | 'new_request';
  data: {
    room_label: string;
    guest_name: string;
    request_type?: string;
  };
  timestamp: string;
}

@Injectable({ providedIn: 'root' })
export class StaySseService {
  private eventSource: EventSource | null = null;

  /** Connect to the SSE stream for a given property. */
  connect(propId: number): Observable<StayNotification> {
    // Close any existing connection
    this.disconnect();

    return new Observable<StayNotification>((observer) => {
      const url = `/api/stay/notifications/stream?prop_id=${propId}`;
      this.eventSource = new EventSource(url, { withCredentials: true });

      this.eventSource.onmessage = (event: MessageEvent) => {
        try {
          const notification: StayNotification = JSON.parse(event.data);
          observer.next(notification);
        } catch {
          // Ignore parse errors (e.g. ping comments)
        }
      };

      this.eventSource.onerror = () => {
        // EventSource auto-reconnects; just notify observer
        // so the component can show an indicator if needed
      };

      this.eventSource.addEventListener('connected', () => {
        // Handshake received — connection established
      });

      return () => {
        this.disconnect();
      };
    });
  }

  /** Close the SSE connection. */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
