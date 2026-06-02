export interface DashboardViewModel {
  kpis: DashboardKpi[];
  latestExecution: {
    executionId: string;
    status: string;
    executedAt: string;
  } | null;
  collectionCounts: Array<{ label: string; value: number }>;
  qualitySummary: Array<{ label: string; value: string }>;
  occupancySummary: Array<{ label: string; value: string; icon?: string }>;
}

export interface DashboardKpi {
  label: string;
  value: string;
  detail: string;
  trend: string;
  direction: 'up' | 'down';
  icon: string;
}
