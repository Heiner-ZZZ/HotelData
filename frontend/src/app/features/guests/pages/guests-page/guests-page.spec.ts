import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { GuestsApiService } from '../../services/guests-api.service';
import { GuestsPageComponent } from './guests-page';

describe('GuestsPageComponent', () => {
  function setup() {
    const router = { navigate: jest.fn() } as unknown as Router;
    const propertyContext = {
      ready: signal(false),
      singleHotelMode: signal(false),
      currentPropId: signal(1),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;
    const api = {} as unknown as GuestsApiService;

    TestBed.configureTestingModule({
      imports: [GuestsPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            queryParamMap: of(convertToParamMap({ prop_id: '1' })),
            snapshot: { queryParamMap: convertToParamMap({ prop_id: '1' }) },
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: GuestsApiService, useValue: api },
      ],
    });
    const fixture = TestBed.createComponent(GuestsPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      http: TestBed.inject(HttpTestingController),
    };
  }

  it('no expone señales locales de banner (message/errorMessage) tras la migración al toast global', () => {
    const { component } = setup();
    expect((component as unknown as Record<string, unknown>).message).toBeUndefined();
    expect((component as unknown as Record<string, unknown>).errorMessage).toBeUndefined();
  });

  it('nunca renderiza banners .notification locales', async () => {
    const ctx = setup();
    ctx.http.expectOne((req) => req.url.includes('/api/management/guests'))
      .flush({ items: [], total: 0, has_next: false });
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();

    const banner = (ctx.fixture.nativeElement as HTMLElement).querySelector('.notification');
    expect(banner).toBeNull();
  });
});
