import { Component, input, output } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-filter-sidebar',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './filter-sidebar.html',
  styleUrl: './filter-sidebar.scss'
})
export class FilterSidebarComponent {
  readonly form = input.required<FormGroup>();
  readonly submitSearch = output<void>();
  readonly resetSearch = output<void>();
}
