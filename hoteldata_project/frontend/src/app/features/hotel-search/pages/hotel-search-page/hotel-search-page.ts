import { Component } from '@angular/core';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { FilterSidebarComponent } from '../../components/filter-sidebar/filter-sidebar';
import { SortControlComponent } from '../../components/sort-control/sort-control';

@Component({
  selector: 'app-hotel-search-page',
  imports: [EmptyStateComponent, FilterSidebarComponent, PageHeaderComponent, SortControlComponent],
  templateUrl: './hotel-search-page.html',
  styleUrl: './hotel-search-page.scss'
})
export class HotelSearchPageComponent {}
