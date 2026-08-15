import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, Subject } from 'rxjs';

import { ClientNotificationsService } from '../../../../../notifications/services/notifications.service';
import type { MyNotificationsDto } from '../../../../../notifications/models/notifications.dto';
import { PpPromotionsTabComponent } from './pp-promotions-tab';

const PAGE_SIZE = 10;

function makeNotification(overrides: Partial<Record<string, unknown>> = {}): Record<string, unknown> {
  return {
    _id: 'notif-1',
    notification_type: 'guest_promotional',
    type_label: 'Promoción',
    recipient_email: 'huesped@example.com',
    recipient_name: 'Huesped',
    booking_id: '',
    prop_id: 1,
    status: 'sent',
    status_label: 'Enviado',
    status_tone: 'success',
    message: '20% de descuento en tu próxima estadía reservando antes del 30 de septiembre.',
    title: 'Oferta de verano',
    is_unread: true,
    error_message: '',
    created_at_iso: '2026-08-13T10:00:00Z',
    ...overrides,
  };
}

function makeDto(
  items: Record<string, unknown>[],
  total?: number,
  page = 1,
  pageSize = PAGE_SIZE,
): MyNotificationsDto {
  const n = total ?? items.length;
  return {
    items: items as MyNotificationsDto['items'],
    total: n,
    unread_count: items.filter((i) => i.is_unread).length,
    page,
    page_size: pageSize,
    total_pages: Math.max(1, Math.ceil(n / pageSize)),
  };
}

function urlFor(page: number): string {
  return `/api/notifications/my?notification_type=guest_promotional&page=${page}&page_size=${PAGE_SIZE}`;
}

describe('PpPromotionsTabComponent', () => {
  let lastFixture: { destroy(): void } | undefined;

  afterEach(() => {
    // Destruye el componente anterior para que su effect/httpResource no
    // contamine el siguiente test (TestBed no lo hace automáticamente aquí).
    lastFixture?.destroy();
    lastFixture = undefined;
    TestBed.resetTestingModule();
  });

  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    TestBed.configureTestingModule({
      imports: [PpPromotionsTabComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ClientNotificationsService,
          useValue: { markAsRead: jest.fn(() => of({ id: 'notif-1', read: true })) },
        },
      ],
    });
    const fixture = TestBed.createComponent(PpPromotionsTabComponent);
    fixture.detectChanges();
    lastFixture = fixture;
    return {
      fixture,
      component: fixture.componentInstance,
      http: TestBed.inject(HttpTestingController),
    };
  }

  async function seed(
    ctx: { http: HttpTestingController; fixture: { detectChanges(): void; whenStable(): Promise<void> } },
    dto: MyNotificationsDto,
  ) {
    ctx.http.expectOne(urlFor(dto.page)).flush(dto);
    // `whenStable()` propaga la respuesta hasta `value()`; el flush posterior
    // corre el effect que acumula la página en `items()`.
    await ctx.fixture.whenStable();
    TestBed.flushEffects();
    ctx.fixture.detectChanges();
  }

  it('pide solo promocionales con el filtro y la paginación del backend', async () => {
    const { fixture, component } = setup();
    await seed(
      { http: TestBed.inject(HttpTestingController), fixture },
      makeDto([makeNotification()]),
    );

    // El backend ya filtra: la petición lleva notification_type=guest_promotional.
    expect(component.items()).toHaveLength(1);
    expect(component.items()[0].notificationType).toBe('guest_promotional');
    expect(component.items()[0].title).toBe('Oferta de verano');

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Oferta de verano');
    expect(text).toContain('20% de descuento');
    expect(text).toContain('1'); // contador de promociones
  });

  it('muestra estado vacío cuando no hay promociones', async () => {
    const { fixture } = setup();
    await seed({ http: TestBed.inject(HttpTestingController), fixture }, makeDto([]));

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Sin promociones todavía');
    expect(fixture.componentInstance.items()).toHaveLength(0);
  });

  it('renderiza hora formateada y dot de no leída en la tarjeta', async () => {
    const { fixture } = setup();
    await seed(
      { http: TestBed.inject(HttpTestingController), fixture },
      makeDto([makeNotification()]),
    );

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.promo-tab-card-dot')).not.toBeNull();
    expect(el.querySelector('.promo-tab-card-time')?.textContent).toContain('2026');
  });

  it('carga la siguiente página con "Cargar más" hasta agotar el total', async () => {
    const { fixture, component } = setup();
    const ctx = { http: TestBed.inject(HttpTestingController), fixture };

    const page1 = Array.from({ length: PAGE_SIZE }, (_, i) =>
      makeNotification({
        created_at_iso: `2026-08-13T${23 - i}:00:00Z`,
        title: `Promo ${i + 1}`,
      }),
    );
    await seed(ctx, makeDto(page1, 12));

    expect(component.items()).toHaveLength(10);
    expect(component.total()).toBe(12);
    expect(component.hasMore()).toBe(true);

    component.loadMore();
    // Flushea el effect del httpResource para que emita la request de la página 2.
    TestBed.flushEffects();
    fixture.detectChanges();
    await seed(
      ctx,
      makeDto(
        [
          makeNotification({ created_at_iso: '2026-08-12T10:00:00Z', title: 'Promo 11' }),
          makeNotification({ created_at_iso: '2026-08-12T09:00:00Z', title: 'Promo 12' }),
        ],
        12,
        2,
      ),
    );

    expect(component.items()).toHaveLength(12);
    expect(component.hasMore()).toBe(false);

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Promo 11');
    expect(text).toContain('Promo 12');
    expect(text).not.toContain('Cargar más');
  });

  it('no muestra "Cargar más" cuando no quedan páginas', async () => {
    const { fixture, component } = setup();
    await seed(
      { http: TestBed.inject(HttpTestingController), fixture },
      makeDto([
        makeNotification({ created_at_iso: '2026-08-13T10:00:00Z', title: 'Promo 1' }),
        makeNotification({ created_at_iso: '2026-08-13T09:00:00Z', title: 'Promo 2' }),
        makeNotification({ created_at_iso: '2026-08-13T08:00:00Z', title: 'Promo 3' }),
      ]),
    );

    expect(component.hasMore()).toBe(false);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('Cargar más');
    expect(text).toContain('Promo 3');
  });

  it('al hacer clic navega a /hotels/{prop_id} y marca la promo como leída', async () => {
    const { fixture, component } = setup();
    const svc = TestBed.inject(ClientNotificationsService) as unknown as {
      markAsRead: jest.Mock;
    };
    const router = TestBed.inject(Router) as unknown as { navigate: jest.Mock };
    await seed(
      { http: TestBed.inject(HttpTestingController), fixture },
      makeDto([makeNotification({ _id: 'notif-1', prop_id: 3 })]),
    );

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.promo-tab-card-dot')).not.toBeNull();
    const item = component.items()[0];

    const card = el.querySelector('.promo-tab-card') as HTMLElement;
    card.click();
    fixture.detectChanges();

    // Deep link Fase 1: la promo lleva a la página pública del hotel.
    expect(router.navigate).toHaveBeenCalledWith(['/hotels', 3]);
    // Y el dot desaparece (marcado en paralelo, sin bloquear la navegación).
    expect(svc.markAsRead).toHaveBeenCalledWith('notif-1');
    expect(component.items()[0].isUnread).toBe(false);
    expect(el.querySelector('.promo-tab-card-dot')).toBeNull();
  });

  it('una tarjeta ya leída navega pero no llama al endpoint de marcado', async () => {
    const { fixture, component } = setup();
    const svc = TestBed.inject(ClientNotificationsService) as unknown as {
      markAsRead: jest.Mock;
    };
    const router = TestBed.inject(Router) as unknown as { navigate: jest.Mock };
    await seed(
      { http: TestBed.inject(HttpTestingController), fixture },
      makeDto([makeNotification({ _id: 'notif-2', is_unread: false })]),
    );

    component.open(component.items()[0]);

    expect(router.navigate).toHaveBeenCalledWith(['/hotels', 1]);
    expect(svc.markAsRead).not.toHaveBeenCalled();
  });
});
