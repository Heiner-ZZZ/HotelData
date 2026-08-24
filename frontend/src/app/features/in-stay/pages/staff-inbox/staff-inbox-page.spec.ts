import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { httpErrorInterceptor } from '../../../../core/api/http-error.interceptor';
import { AuthService } from '../../../../core/auth/auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { InStayApiService } from '../../services/in-stay-api.service';
import { StaySseService } from '../../services/stay-sse.service';
import { ExpensesApiService } from '../../../expenses/services/expenses-api.service';
import {
  StaffInboxPageComponent,
  classifyConversation,
  CHAT_BUCKET_META,
} from './staff-inbox-page';
import type { Conversation, ServiceRequest } from '../../models/in-stay.model';

// Fechas RELATIVAS al día de ejecución: el componente clasifica contra
// ``todayDate = new Date().toISOString().slice(0, 10)`` — fechas fijas
// se volvían flakies cuando el calendario avanzaba (check_out == today).
const today = new Date().toISOString().slice(0, 10);
const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
const tomorrow = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
const twoDaysAgo = new Date(Date.now() - 2 * 86_400_000).toISOString().slice(0, 10);

function makeConversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    _id: 'HR-1-101',
    booking_id: 'BK-1',
    prop_id: 1,
    guest_name: 'Guest Test',
    last_message: 'Hello',
    last_sender: 'guest',
    last_time: `${today}T10:00:00`,
    message_count: 1,
    unread: 1,
    dnd: false,
    check_in: yesterday,
    check_out: tomorrow,
    stay_status: 'checked_in',
    ...overrides,
  };
}

describe('classifyConversation', () => {
  it('clasifica como history cuando check_out ya pasó, aunque stay_status siga checked_in', () => {
    const c = makeConversation({ stay_status: 'checked_in', check_in: twoDaysAgo, check_out: yesterday });
    expect(classifyConversation(c, today)).toBe('history');
  });

  it('clasifica como history cuando stay_status quedó pending pero check_out ya pasó', () => {
    const c = makeConversation({ stay_status: 'pending', check_in: twoDaysAgo, check_out: yesterday });
    expect(classifyConversation(c, today)).toBe('history');
  });

  it('clasifica estados finalizados como history aunque check_out sea futuro', () => {
    for (const status of ['checked_out', 'no_show', 'cancelled']) {
      const c = makeConversation({ stay_status: status, check_in: yesterday, check_out: tomorrow });
      expect(classifyConversation(c, today)).toBe('history');
    }
  });

  it('clasifica check-in de hoy como today', () => {
    const c = makeConversation({ stay_status: 'pending', check_in: today, check_out: tomorrow });
    expect(classifyConversation(c, today)).toBe('today');
  });

  it('clasifica check-out de hoy como today', () => {
    const c = makeConversation({ stay_status: 'checked_in', check_in: yesterday, check_out: today });
    expect(classifyConversation(c, today)).toBe('today');
  });

  it('clasifica estadía en curso como active', () => {
    const c = makeConversation({ stay_status: 'checked_in', check_in: yesterday, check_out: tomorrow });
    expect(classifyConversation(c, today)).toBe('active');
  });

  it('ignora la fecha del último mensaje: una estadía activa con mensaje viejo sigue siendo active', () => {
    const c = makeConversation({ stay_status: 'checked_in', check_in: yesterday, check_out: tomorrow, last_time: `${twoDaysAgo}T10:00:00` });
    expect(classifyConversation(c, today)).toBe('active');
  });
});

describe('StaffInboxPageComponent — filtros de chat', () => {
  let component: StaffInboxPageComponent;
  let mockApi: any;
  let mockLedgerFolios: jest.Mock;
  let navigate: jest.Mock;

  function makeRequest(overrides: Partial<ServiceRequest> = {}): ServiceRequest {
    return {
      _id: 'REQ-1',
      booking_id: 'BK-1',
      prop_id: 1,
      room_label: 'HR-1-101',
      request_type: 'housekeeping',
      request_type_label: 'Limpieza',
      description: 'Need extra towels',
      status: 'pending',
      status_label: 'Pendiente',
      staff_response: '',
      created_at: `${today}T09:00:00`,
      resolved_at: null,
      ...overrides,
    };
  }

  beforeEach(async () => {
    navigate = jest.fn();
    mockLedgerFolios = jest.fn().mockReturnValue(of({ items: [] }));
    mockApi = {
      listConversations: jest.fn().mockReturnValue(of({ conversations: [] })),
      listRequests: jest.fn().mockReturnValue(of({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 })),
      getConversationMessages: jest.fn().mockReturnValue(of({ messages: [] })),
      staffReply: jest.fn().mockReturnValue(of({})),
      updateRequest: jest.fn().mockReturnValue(of({})),
      listSessions: jest.fn().mockReturnValue(of({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 })),
      createSession: jest.fn().mockReturnValue(of({})),
      deactivateSession: jest.fn().mockReturnValue(of({})),
      listLostFound: jest.fn().mockReturnValue(of({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 })),
      createLostItem: jest.fn().mockReturnValue(of({})),
      claimLostItem: jest.fn().mockReturnValue(of({})),
      disposeLostItem: jest.fn().mockReturnValue(of({})),
      staffCreateRequest: jest.fn().mockReturnValue(of({})),
    };

    TestBed.overrideComponent(PropertySelectorComponent, {
      set: { template: '<span>selector-stub</span>' },
    });

    await TestBed.configureTestingModule({
      imports: [StaffInboxPageComponent],
      providers: [
        provideHttpClient(withInterceptors([httpErrorInterceptor])),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { url: [], paramMap: { get: () => null } }, paramMap: of(new Map()) } },
        { provide: Router, useValue: { events: of(), navigate } },
        { provide: ToastService, useValue: { success: jest.fn(), error: jest.fn(), warning: jest.fn(), info: jest.fn() } },
        { provide: AuthService, useValue: { hasPermission: () => true } },
        {
          provide: PropertyContextService,
          useValue: {
            currentPropId: signal(1),
            currentPropLabel: signal(''),
            mode: signal('all'),
            ready: signal(true),
            assignedProperties: signal([]),
            defaultPropId: signal(0),
            singleHotelMode: signal(false),
            setProperty: jest.fn(),
            clear: jest.fn(),
          },
        },
        { provide: InStayApiService, useValue: mockApi },
        { provide: StaySseService, useValue: { connect: () => of(), disconnect: jest.fn() } },
        { provide: ExpensesApiService, useValue: { getLedgerFolios: mockLedgerFolios, postFolioPayment: () => of({}), transferFolioCharges: () => of({}) } },
      ],
    }).compileComponents();

    component = TestBed.createComponent(StaffInboxPageComponent).componentInstance;
  });

  it('no dispara conversaciones/solicitudes con prop_id=0 (el backend responde 422 con ge=1)', () => {
    // Contexto aún sin hidratar: currentPropId arranca en 0.
    (component as any).propCtx.currentPropId.set(0);
    const fresh = TestBed.createComponent(StaffInboxPageComponent);
    fresh.detectChanges();

    // El burst inicial del constructor NO debe golpear la API sin propiedad.
    expect(mockApi.listConversations).not.toHaveBeenCalledWith(0);
    expect(mockApi.listRequests).not.toHaveBeenCalledWith(0);

    // Al seleccionar una propiedad sí carga con el id real (el servicio real
    // actualiza la signal en setProperty; el mock es pasivo).
    (component as any).propCtx.currentPropId.set(3);
    (fresh.componentInstance as any).loadData();
    expect(mockApi.listConversations).toHaveBeenCalledWith(3);
    expect(mockApi.listRequests).toHaveBeenCalledWith(3, undefined);
    expect(mockApi.listConversations).not.toHaveBeenCalledWith(0);
    expect(mockApi.listRequests).not.toHaveBeenCalledWith(0);
  });

  it('agrupa conversaciones en los 3 buckets según la fecha de la reserva', () => {
    const active = makeConversation({ _id: 'HR-1-101', stay_status: 'checked_in', check_in: yesterday, check_out: tomorrow });
    const hoy = makeConversation({ _id: 'HR-1-102', stay_status: 'pending', check_in: today, check_out: tomorrow });
    const historial = makeConversation({ _id: 'HR-1-103', stay_status: 'checked_in', check_in: twoDaysAgo, check_out: yesterday });

    mockApi.listConversations.mockReturnValue(of({ conversations: [active, hoy, historial] }));
    (component as any).loadData();

    expect(component.conversationBuckets().active.map((c) => c._id)).toEqual(['HR-1-101']);
    expect(component.conversationBuckets().today.map((c) => c._id)).toEqual(['HR-1-102']);
    expect(component.conversationBuckets().history.map((c) => c._id)).toEqual(['HR-1-103']);
  });

  it('envía al historial una reserva con stay_status pending cuyo check_out ya pasó', () => {
    const stuck = makeConversation({ _id: 'HR-1-109', stay_status: 'pending', check_in: twoDaysAgo, check_out: yesterday });

    mockApi.listConversations.mockReturnValue(of({ conversations: [stuck] }));
    (component as any).loadData();

    expect(component.conversationBuckets().history.map((c) => c._id)).toEqual(['HR-1-109']);
    expect(component.conversationBuckets().active).toEqual([]);
  });

  it('muestra todos los buckets por defecto (sin filtro)', () => {
    const active = makeConversation({ _id: 'HR-1-101' });
    const historial = makeConversation({ _id: 'HR-1-103', check_in: twoDaysAgo, check_out: yesterday });

    mockApi.listConversations.mockReturnValue(of({ conversations: [active, historial] }));
    (component as any).loadData();

    expect(component.visibleChatGroups().map((g) => g.id)).toEqual(['active', 'history']);
  });

  it('filtra a un solo bucket cuando se elige un filtro de chat', () => {
    const active = makeConversation({ _id: 'HR-1-101' });
    const historial = makeConversation({ _id: 'HR-1-103', check_in: twoDaysAgo, check_out: yesterday });

    mockApi.listConversations.mockReturnValue(of({ conversations: [active, historial] }));
    (component as any).loadData();

    component.setChatFilter('history');

    expect(component.visibleChatGroups().map((g) => g.id)).toEqual(['history']);
    expect(component.visibleChatGroups()[0].conversations.map((c) => c._id)).toEqual(['HR-1-103']);
  });

  it('excluye el bucket filtrado cuando está vacío', () => {
    const active = makeConversation({ _id: 'HR-1-101' });
    mockApi.listConversations.mockReturnValue(of({ conversations: [active] }));
    (component as any).loadData();

    component.setChatFilter('history');

    expect(component.visibleChatGroups()).toEqual([]);
  });

  it('cambia de tab localmente sin navegar (sin recargo de interfaz)', () => {
    component.setTab('folios');

    expect(component.activeTab()).toBe('folios');
    expect(navigate).not.toHaveBeenCalled();
  });

  describe('chip Cerrados de folios', () => {
    it('el chip Cerrados consulta todos los estados no abiertos (closed, settled, written_off)', () => {
      mockLedgerFolios.mockReturnValue(of({ items: [] }));

      component.setTab('folios');
      component.setFolioStatusFilter('closed');

      expect(mockLedgerFolios).toHaveBeenCalledWith(1, 'closed,settled,written_off');
    });

    it('el chip Cerrados muestra los folios closed, settled y written_off devueltos por la API', () => {
      mockLedgerFolios.mockReturnValue(of({
        items: [
          { folioRef: 'F-1', guestName: 'Guest A', status: 'closed', balance: 0, transactionCount: 1 },
          { folioRef: 'F-2', guestName: 'Guest B', status: 'settled', balance: 0, transactionCount: 2 },
          { folioRef: 'F-3', guestName: 'Guest C', status: 'written_off', balance: 0, transactionCount: 3 },
        ],
      }));

      component.setTab('folios');
      component.setFolioStatusFilter('closed');

      expect(component.folios().map((f) => f.status)).toEqual(['closed', 'settled', 'written_off']);
      expect(component.folios().length).toBe(3);
    });

    it('el chip Abiertos sigue consultando solo folios open', () => {
      mockLedgerFolios.mockClear();
      component.setTab('folios');
      component.setFolioStatusFilter('open');

      expect(mockLedgerFolios).toHaveBeenCalledWith(1, 'open');
    });
  });
});

describe('StaffInboxPageComponent — template', () => {
  let navigate: jest.Mock;
  let mockLedgerFolios: jest.Mock;

  beforeEach(async () => {
    navigate = jest.fn();
    mockLedgerFolios = jest.fn().mockReturnValue(of({ items: [] }));
    const mockApi = {
      listConversations: jest.fn().mockReturnValue(of({ conversations: [] })),
      listRequests: jest.fn().mockReturnValue(of({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 })),
      getConversationMessages: jest.fn().mockReturnValue(of({ messages: [] })),
      listSessions: jest.fn().mockReturnValue(of({ items: [] })),
      listLostFound: jest.fn().mockReturnValue(of({ items: [] })),
    };

    TestBed.overrideComponent(PropertySelectorComponent, {
      set: { template: '<span>selector-stub</span>' },
    });

    await TestBed.configureTestingModule({
      imports: [StaffInboxPageComponent],
      providers: [
        provideHttpClient(withInterceptors([httpErrorInterceptor])),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { url: [], paramMap: { get: () => null } }, paramMap: of(new Map()) } },
        { provide: Router, useValue: { events: of(), navigate } },
        { provide: ToastService, useValue: { success: jest.fn(), error: jest.fn(), warning: jest.fn(), info: jest.fn() } },
        { provide: AuthService, useValue: { hasPermission: () => true } },
        {
          provide: PropertyContextService,
          useValue: {
            currentPropId: signal(1),
            currentPropLabel: signal(''),
            mode: signal('all'),
            ready: signal(true),
            assignedProperties: signal([]),
            defaultPropId: signal(0),
            singleHotelMode: signal(false),
            setProperty: jest.fn(),
            clear: jest.fn(),
          },
        },
        { provide: InStayApiService, useValue: mockApi },
        { provide: StaySseService, useValue: { connect: () => of(), disconnect: jest.fn() } },
        { provide: ExpensesApiService, useValue: { getLedgerFolios: mockLedgerFolios, postFolioPayment: () => of({}), transferFolioCharges: () => of({}) } },
      ],
    }).compileComponents();
  });

  it('renderiza los tabs como botones, no como enlaces', () => {
    const fixture = TestBed.createComponent(StaffInboxPageComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('a.si-tab')).toBeNull();
    expect(fixture.nativeElement.querySelectorAll('button.si-tab').length).toBeGreaterThan(0);
  });

  it('muestra los chips de filtro de chat (Todas + 3 buckets)', () => {
    const fixture = TestBed.createComponent(StaffInboxPageComponent);
    fixture.detectChanges();

    const chips = fixture.nativeElement.querySelectorAll('.si-chat-filter .si-chip');
    // 3 buckets + "Todas"
    expect(chips.length).toBe(CHAT_BUCKET_META.length + 1);
  });
});

describe('StaffInboxPageComponent — nombre del huésped en el chat', () => {
  let navigate: jest.Mock;
  let mockApi: Record<string, jest.Mock>;

  beforeEach(async () => {
    navigate = jest.fn();
    mockApi = {
      listConversations: jest.fn().mockReturnValue(of({ conversations: [] })),
      listRequests: jest.fn().mockReturnValue(of({ items: [], total: 0, page: 1, page_size: 20, total_pages: 1 })),
      getConversationMessages: jest.fn().mockReturnValue(of({ messages: [] })),
      listSessions: jest.fn().mockReturnValue(of({ items: [] })),
      listLostFound: jest.fn().mockReturnValue(of({ items: [] })),
    };

    TestBed.overrideComponent(PropertySelectorComponent, {
      set: { template: '<span>selector-stub</span>' },
    });

    await TestBed.configureTestingModule({
      imports: [StaffInboxPageComponent],
      providers: [
        provideHttpClient(withInterceptors([httpErrorInterceptor])),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { url: [], paramMap: { get: () => null } }, paramMap: of(new Map()) } },
        { provide: Router, useValue: { events: of(), navigate } },
        { provide: ToastService, useValue: { success: jest.fn(), error: jest.fn(), warning: jest.fn(), info: jest.fn() } },
        { provide: AuthService, useValue: { hasPermission: () => true } },
        {
          provide: PropertyContextService,
          useValue: {
            currentPropId: signal(1),
            currentPropLabel: signal(''),
            mode: signal('all'),
            ready: signal(true),
            assignedProperties: signal([]),
            defaultPropId: signal(0),
            singleHotelMode: signal(false),
            setProperty: jest.fn(),
            clear: jest.fn(),
          },
        },
        { provide: InStayApiService, useValue: mockApi },
        { provide: StaySseService, useValue: { connect: () => of(), disconnect: jest.fn() } },
        { provide: ExpensesApiService, useValue: { getLedgerFolios: jest.fn().mockReturnValue(of({ items: [] })), postFolioPayment: () => of({}), transferFolioCharges: () => of({}) } },
      ],
    }).compileComponents();
  });

  function makeMessage(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
      _id: 'M-1',
      booking_id: 'BK-1',
      prop_id: 1,
      room_label: 'HR-1-101',
      sender: 'guest',
      staff_name: '',
      guest_name: '',
      message: 'Hola hotel',
      created_at: `${today}T10:00:00`,
      read: false,
      ...overrides,
    };
  }

  function renderWithConversation() {
    const conv = makeConversation({ _id: 'HR-1-101', guest_name: 'Juan Pérez' });
    mockApi.listConversations.mockReturnValue(of({ conversations: [conv] }));
    const fixture = TestBed.createComponent(StaffInboxPageComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('la burbuja de un mensaje de huésped muestra su nombre como autor', () => {
    mockApi.getConversationMessages.mockReturnValue(of({
      messages: [makeMessage({ sender: 'guest', guest_name: 'Juan Pérez' })],
    }));
    const fixture = renderWithConversation();
    fixture.componentInstance.selectConversation('HR-1-101');
    fixture.detectChanges();

    const authors = Array.from(fixture.nativeElement.querySelectorAll('.si-msg-author'))
      .map((n) => (n as HTMLElement).textContent?.trim());
    expect(authors).toContain('Juan Pérez');
  });

  it('el header del chat muestra el nombre del huésped junto a la habitación', () => {
    mockApi.getConversationMessages.mockReturnValue(of({ messages: [] }));
    const fixture = renderWithConversation();
    fixture.componentInstance.selectConversation('HR-1-101');
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.si-chat-room')?.textContent).toContain('Juan Pérez');
  });

  it('la burbuja staff sigue mostrando staff_name y no el nombre del huésped', () => {
    mockApi.getConversationMessages.mockReturnValue(of({
      messages: [
        makeMessage({ sender: 'staff', staff_name: 'Recepción' }),
        makeMessage({ sender: 'guest', guest_name: 'Juan Pérez', message: 'ok' }),
      ],
    }));
    const fixture = renderWithConversation();
    fixture.componentInstance.selectConversation('HR-1-101');
    fixture.detectChanges();

    const authors = Array.from(fixture.nativeElement.querySelectorAll('.si-msg-author'))
      .map((n) => (n as HTMLElement).textContent?.trim());
    expect(authors).toContain('Recepción');
    // El autor del huésped solo va en SU burbuja; la de staff no lo repite.
    const staffBubble = fixture.nativeElement.querySelector('.si-msg.staff .si-msg-bubble');
    expect(staffBubble?.textContent).toContain('Recepción');
    expect(staffBubble?.textContent).not.toContain('Juan Pérez');
  });
});


