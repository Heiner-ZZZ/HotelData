import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ProductsAuthService } from '../../services/products-auth.service';

@Component({
  selector: 'app-products-section-nav',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './products-section-nav.html',
  styleUrl: './products-section-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductsSectionNavComponent {
  private readonly propCtx = inject(PropertyContextService);
  private readonly productsAuth = inject(ProductsAuthService);

  readonly propId = computed(() => this.propCtx.currentPropId());
  readonly canSeeCost = this.productsAuth.canSeeCost;

  /** Query params for all tabs — keeps ?prop_id synced. Null removes the param when no hotel selected. */
  readonly queryParams = computed(() => {
    const pid = this.propId();
    return pid ? { prop_id: pid } : {};
  });
}
