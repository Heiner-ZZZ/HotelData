import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map, switchMap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { PropertyFactsPanelComponent } from '../../components/property-facts-panel/property-facts-panel';
import type { PropertyDetailViewModel } from '../../models/properties.model';
import { PropertiesApiService } from '../../services/properties-api.service';

@Component({
  selector: 'app-property-detail-page',
  standalone: true,
  imports: [
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertyFactsPanelComponent,
    RouterLink
  ],
  templateUrl: './property-detail-page.html',
  styleUrl: './property-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PropertyDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(PropertiesApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<PropertyDetailViewModel | null>(null);

  constructor() {
    this.route.paramMap
      .pipe(
        map((params) => Number(params.get('propertyId'))),
        switchMap((propId) => {
          this.viewState.set('loading');
          return this.api.getPropertyDetail(propId);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set('success');
        },
        error: () => this.viewState.set('error')
      });
  }
}
