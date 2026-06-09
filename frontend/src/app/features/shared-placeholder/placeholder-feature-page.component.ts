import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { EmptyStateComponent } from '../../shared/ui/empty-state/empty-state';
import { PageHeaderComponent } from '../../shared/ui/page-header/page-header';

@Component({
  selector: 'app-placeholder-feature-page',
  imports: [EmptyStateComponent, PageHeaderComponent],
  template: `
    <div class="placeholder-page">
      <app-page-header [title]="title" description="Ruta preparada dentro de la nueva arquitectura Angular." />
      <app-empty-state [title]="title" [description]="description" />
    </div>
  `,
  styles: '.placeholder-page { display: grid; gap: 1.5rem; }'
})
export class PlaceholderFeaturePageComponent {
  private readonly route = inject(ActivatedRoute);

  readonly title = this.route.snapshot.data['title'] as string;
  readonly description = this.route.snapshot.data['description'] as string;
}
