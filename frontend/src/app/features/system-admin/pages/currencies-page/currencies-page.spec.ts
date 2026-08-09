import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { CurrenciesApiService } from '../../services/currencies-api.service';
import type { Currency } from '../../models/currencies.model';
import { CurrenciesPageComponent } from './currencies-page';

describe('CurrenciesPageComponent', () => {
  const mxn: Currency = { code: 'MXN', name: 'Peso mexicano', symbol: '$', decimals: 2, active: true };
  const clp: Currency = { code: 'CLP', name: 'Peso chileno', symbol: '$', decimals: 0, active: true };
  const usd: Currency = { code: 'USD', name: 'Dólar estadounidense', symbol: '$', decimals: 2, active: false };

  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as never;

    const api = {
      toggle: jest.fn(),
      delete: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
    };
    const toast = { success: jest.fn(), error: jest.fn() };

    TestBed.configureTestingModule({
      imports: [CurrenciesPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        { provide: CurrenciesApiService, useValue: api },
        { provide: ToastService, useValue: toast },
      ],
    });

    const fixture = TestBed.createComponent(CurrenciesPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    return {
      fixture,
      component,
      mode: TestBed.inject(OperationModeService),
      confirmDialog: TestBed.inject(ConfirmDialogService),
      http: TestBed.inject(HttpTestingController),
      api,
      toast,
    };
  }

  /** Seed the httpResource response with a fixed currency catalog.
   *  httpResource publishes its value asynchronously (microtask after the
   *  HTTP response), so the caller must await before asserting computeds. */
  async function seedCurrencies(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }, list: Currency[]) {
    ctx.http.expectOne('/api/management/currencies').flush({ currencies: list });
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  /** Yield microtasks so awaited continuations (dialog confirm) resume. */
  const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

  it('shows the read chip by default', () => {
    const { mode } = setup();
    expect(mode.mode()).toBe('read');
  });

  it('switches the nav chip to insert mode when opening the create modal', () => {
    const { component, mode } = setup();
    component.openAdd();
    expect(mode.mode()).toBe('insert');
    expect(mode.detail()).toBe('Nueva moneda');
  });

  it('switches the nav chip to update mode with the currency code when editing', () => {
    const { component, mode } = setup();
    component.openEdit(mxn);
    expect(mode.mode()).toBe('update');
    expect(mode.detail()).toBe('MXN');
  });

  it('restores read mode when the modal closes', () => {
    const { component, mode } = setup();
    component.openAdd();
    expect(mode.mode()).toBe('insert');
    component.closeModal();
    expect(mode.mode()).toBe('read');
  });

  it('keeps the chip in delete mode while the confirmation is open and deletes after confirm', async () => {
    const { component, mode, confirmDialog, api } = setup();
    api.delete.mockReturnValue({ subscribe: () => ({}) });

    component.requestDelete(mxn);

    expect(confirmDialog.isOpen()).toBe(true);
    expect(mode.mode()).toBe('delete');
    expect(mode.detail()).toBe('MXN');

    confirmDialog.confirm();
    await flush();

    expect(api.delete).toHaveBeenCalledWith('MXN');
    expect(mode.mode()).toBe('read');
  });

  it('does not delete when the confirmation is cancelled', async () => {
    const { component, confirmDialog, api } = setup();
    api.delete.mockReturnValue({ subscribe: () => ({}) });

    component.requestDelete(mxn);
    confirmDialog.cancel();
    await flush();

    expect(api.delete).not.toHaveBeenCalled();
    expect(component.showModal()).toBe(false);
  });

  it('shows update mode while a toggle request is in flight and restores read mode after', () => {
    const { component, mode, api } = setup();
    const pending = new Subject<Currency>();
    api.toggle.mockReturnValue(pending);

    component.toggle(mxn);
    expect(mode.mode()).toBe('update');
    expect(mode.detail()).toBe('MXN');

    pending.next(mxn);
    pending.complete();
    expect(mode.mode()).toBe('read');
  });

  it('computes catalog stats (total, active, zero-decimal)', async () => {
    const ctx = setup();
    await seedCurrencies(ctx, [mxn, clp, usd]);

    expect(ctx.component.stats().total).toBe(3);
    expect(ctx.component.stats().active).toBe(2);
    expect(ctx.component.stats().zeroDecimal).toBe(1);
  });

  it('filters currencies by search query over code and name', async () => {
    const ctx = setup();
    await seedCurrencies(ctx, [mxn, clp, usd]);

    ctx.component.search.set('mexi');
    expect(ctx.component.filteredCurrencies().map((c) => c.code)).toEqual(['MXN']);

    ctx.component.search.set('USD');
    expect(ctx.component.filteredCurrencies().map((c) => c.code)).toEqual(['USD']);
  });

  it('filters currencies by active status', async () => {
    const ctx = setup();
    await seedCurrencies(ctx, [mxn, clp, usd]);

    ctx.component.statusFilter.set('inactive');
    expect(ctx.component.filteredCurrencies().map((c) => c.code)).toEqual(['USD']);

    ctx.component.statusFilter.set('active');
    expect(ctx.component.filteredCurrencies().map((c) => c.code)).toEqual(['MXN', 'CLP']);
  });

  it('toasts "Moneda creada" after saving a new currency and closes the modal', async () => {
    const { component, api, toast } = setup();
    const pending = new Subject<Currency>();
    api.create.mockReturnValue(pending);

    component.openAdd();
    component.form.set({ code: 'ARS', name: 'Peso argentino', symbol: '$', decimals: 2 });
    component.save();

    expect(api.create).toHaveBeenCalledWith({
      code: 'ARS',
      name: 'Peso argentino',
      symbol: '$',
      decimals: 2,
    });

    pending.next(mxn);
    pending.complete();
    await flush();

    expect(component.showModal()).toBe(false);
    expect(toast.success).toHaveBeenCalledWith('Moneda creada');
  });

  it('toasts "Moneda actualizada" when editing (regression: closeModal must not null the code first)', async () => {
    const { component, api, toast } = setup();
    const pending = new Subject<Currency>();
    api.update.mockReturnValue(pending);

    component.openEdit(mxn);
    component.form.set({ code: 'MXN', name: 'Peso mexicano nuevo', symbol: '$', decimals: 2 });
    component.save();

    expect(api.update).toHaveBeenCalledWith('MXN', {
      name: 'Peso mexicano nuevo',
      symbol: '$',
      decimals: 2,
    });

    pending.next(mxn);
    pending.complete();
    await flush();

    expect(component.showModal()).toBe(false);
    expect(toast.success).toHaveBeenCalledWith('Moneda actualizada');
  });

  it('renders a deterministic formatted amount preview from symbol and decimals', () => {
    const { component } = setup();

    expect(component.formatPreview({ symbol: '$', decimals: 2 })).toBe('$1.234,50');
    expect(component.formatPreview({ symbol: '$', decimals: 0 })).toBe('$1.235');
    expect(component.formatPreview({ symbol: '¥', decimals: 0 })).toBe('¥1.235');
  });
});
