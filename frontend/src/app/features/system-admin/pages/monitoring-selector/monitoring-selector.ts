import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Router } from '@angular/router';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';

interface PipelineOption {
  id: string;
  route: string;
  icon: string;
  title: string;
  description: string;
  detail: string;
  accent: string;
}

@Component({
  selector: 'app-monitoring-selector',
  imports: [PageHeaderComponent],
  templateUrl: './monitoring-selector.html',
  styleUrl: './monitoring-selector.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonitoringSelectorComponent {
  private readonly router = inject(Router);

  readonly pipelines: PipelineOption[] = [
    {
      id: 'pocketbase_to_mongo',
      route: '/system/monitoring/pocketbase_to_mongo',
      icon: 'sync_alt',
      title: 'PocketBase → MongoDB',
      description: 'ETL GA03: preparación CSV, validación y carga del dataset operacional.',
      detail: 'Operacional · manual · Airflow DAG hoteldata_ga03_etl',
      accent: 'mongo',
    },
    {
      id: 'mongo_to_clickhouse',
      route: '/system/monitoring/mongo_to_clickhouse',
      icon: 'monitoring',
      title: 'MongoDB → ClickHouse',
      description: 'ETL táctico: KPIs y agregaciones diarias para los informes compuestos de TA12.',
      detail: 'Táctico · horario · Airflow DAG hoteldata_mongo_to_clickhouse_etl',
      accent: 'clickhouse',
    },
  ];

  open(pipeline: PipelineOption) {
    void this.router.navigate([pipeline.route]);
  }
}
