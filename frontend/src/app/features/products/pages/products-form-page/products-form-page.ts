import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';

import { ProductsApiService } from '../../services/products-api.service';
import type {
  CreateHotelProductPayload,
  UpdateHotelProductPayload,
} from '../../models/products.dto';
import type { HotelProduct, ProductType } from '../../models/products.model';
import { PRODUCT_TYPE_LABELS } from '../../models/products.model';

const CATEGORY_OPTIONS = [
  'Minibar',
  'Spa',
  'Restaurante',
  'Lavandería',
  'Parking',
  'Mascotas',
  'Room Service',
  'Daños',
  'Late Checkout',
  'Extras',
  'Otros',
];

@Component({
  selector: 'app-products-form-page',
  imports: [
    RouterLink,
    ReactiveFormsModule,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent
  ],
  templateUrl: './products-form-page.html',
  styleUrl: './products-form-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductsFormPageComponent implements OnInit {
  private readonly propCtx = inject(PropertyContextService);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly productsApi = inject(ProductsApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);

  readonly CATEGORY_OPTIONS = CATEGORY_OPTIONS;
  readonly PRODUCT_TYPE_LABELS = PRODUCT_TYPE_LABELS;
  readonly PRODUCT_TYPES: ProductType[] = ['retail', 'supply', 'asset'];

  /** Edit mode if `productId` is in the URL; otherwise create mode. */
  readonly editProductId = signal<string | null>(null);
  readonly isEditMode = computed(() => !!this.editProductId());

  /** Page header labels. */
  readonly pageTitle = computed(() => (this.isEditMode() ? 'Editar producto' : 'Nuevo producto'));
  readonly pageSubtitle = computed(() =>
    this.isEditMode() ? 'Modifica los datos del producto seleccionado.' : 'Crea un nuevo producto en el catálogo.'
  );

  /** Reactive form. */
  readonly form: FormGroup = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    description: ['', []],
    category: ['Otros', [Validators.required]],
    type: ['retail' as ProductType, [Validators.required]],
    cost_price: [0, [Validators.required, Validators.min(0)]],
    unit_price: [0, [Validators.required, Validators.min(0)]],
    quantity_available: [0, [Validators.required, Validators.min(0)]],
    default_supplier: ['', []],
    supplier_sku: ['', []],
    par_level: [null as number | null, [Validators.min(0)]],
    is_active: [true, []],
  });

  /** State for saving / loading the existing product / error. */
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly submitError = signal<string | null>(null);

  /** Live margin preview — recomputed via a trigger signal that the
   *  valueChanges subscription increments on every input change. */
  readonly marginTrigger = signal(0);
  readonly marginPreview = computed(() => {
    this.marginTrigger(); // explicit dependency on the trigger
    const cost = Number(this.form.controls['cost_price'].value ?? 0);
    const retail = Number(this.form.controls['unit_price'].value ?? 0);
    return retail - cost;
  });
  readonly marginPctPreview = computed(() => {
    this.marginTrigger();
    const cost = Number(this.form.controls['cost_price'].value ?? 0);
    const retail = Number(this.form.controls['unit_price'].value ?? 0);
    if (retail <= 0) return 0;
    return ((retail - cost) / retail) * 100;
  });

  constructor() {
    // Wire valueChanges → marginTrigger so the computed preview re-renders.
    this.form.controls['cost_price'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.marginTrigger.update((n) => n + 1));
    this.form.controls['unit_price'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.marginTrigger.update((n) => n + 1));
  }

  ngOnInit(): void {
    const pid = this.activatedRoute.snapshot.paramMap.get('productId');
    if (pid) {
      this.editProductId.set(pid);
      this.loadProduct(pid);
    }
  }

  private loadProduct(productId: string): void {
    const propId = this.propCtx.currentPropId();
    if (!propId) return;
    this.loading.set(true);
    this.loadError.set(null);
    this.productsApi
      .listHotelProducts(propId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (products) => {
          const p = products.find((x) => x.productId === productId);
          if (!p) {
            this.loadError.set('Producto no encontrado.');
          } else {
            this.patchForm(p);
          }
          this.loading.set(false);
        },
        error: () => {
          this.loadError.set('No se pudo cargar el producto.');
          this.loading.set(false);
        },
      });
  }

  private patchForm(p: HotelProduct): void {
    this.form.patchValue({
      name: p.name,
      description: p.description,
      category: p.category,
      type: p.type,
      cost_price: p.costPrice,
      unit_price: p.unitPrice,
      quantity_available: p.quantityAvailable,
      default_supplier: p.defaultSupplier ?? '',
      supplier_sku: p.supplierSku ?? '',
      par_level: p.parLevel,
      is_active: p.isActive,
    });
  }

  fieldError(fieldName: string): string | null {
    const ctrl = this.form.get(fieldName);
    if (!ctrl || !ctrl.touched || ctrl.valid) return null;
    if (ctrl.hasError('required')) return 'Requerido';
    if (ctrl.hasError('minlength')) return 'Mínimo 2 caracteres';
    if (ctrl.hasError('min')) return 'Debe ser ≥ 0';
    return 'Valor inválido';
  }

  async save(): Promise<void> {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }
    const propId = this.propCtx.currentPropId();
    if (!propId) return;

    const v = this.form.getRawValue();
    const ok = await this.confirmDialog.open({
      title: this.isEditMode() ? 'Guardar cambios' : 'Crear producto',
      message: this.isEditMode()
        ? `¿Guardar cambios en "${v.name}"?`
        : `¿Crear "${v.name}" en el catálogo?`,
      confirmLabel: this.isEditMode() ? 'Guardar' : 'Crear',
      variant: 'default',
    });
    if (!ok) return;

    this.saving.set(true);
    this.submitError.set(null);

    const basePayload = {
      name: v.name,
      description: v.description,
      category: v.category,
      type: v.type,
      cost_price: Number(v.cost_price),
      unit_price: Number(v.unit_price),
      quantity_available: Number(v.quantity_available),
      default_supplier: v.default_supplier || null,
      supplier_sku: v.supplier_sku || null,
      par_level: v.par_level === null || v.par_level === undefined || Number.isNaN(v.par_level) ? null : Number(v.par_level),
      is_active: !!v.is_active,
    };

    if (this.isEditMode()) {
      const update: UpdateHotelProductPayload = basePayload;
      this.productsApi
        .updateHotelProduct(propId, this.editProductId()!, update)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => this.navigateBack(),
          error: () => {
            this.submitError.set('Error al guardar cambios.');
            this.saving.set(false);
          },
        });
    } else {
      const create: CreateHotelProductPayload = basePayload;
      this.productsApi
        .createHotelProduct(propId, create)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => this.navigateBack(),
          error: () => {
            this.submitError.set('Error al crear el producto.');
            this.saving.set(false);
          },
        });
    }
  }

  private navigateBack(): void {
    this.saving.set(false);
    const propId = this.propCtx.currentPropId();
    this.router.navigate(['/management/products'], {
      queryParams: propId ? { prop_id: propId } : {}
    });
  }

  cancel(): void {
    this.navigateBack();
  }
}