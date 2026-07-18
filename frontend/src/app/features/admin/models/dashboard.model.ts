export interface DashboardViewModel {
  kpis: DashboardKpi[];
  latestExecution: {
    executionId: string;
    status: string;
    executedAt: string;
  } | null;
  collectionCounts: { label: string; value: number }[];
  operationalCounts: { label: string; value: number }[];
  qualitySummary: { label: string; value: string }[];
  occupancySummary: { label: string; value: string; icon?: string }[];
}

export interface DashboardKpi {
  label: string;
  value: string;
  detail: string;
  trend: string;
  direction: 'up' | 'down';
  icon: string;
}
