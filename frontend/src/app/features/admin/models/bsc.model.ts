export interface BscKpi {
  label: string;
  value: string;
  unit: string;
  target: string;
  detail: string;
  semaforo: 'green' | 'yellow' | 'red';
  trend: 'up' | 'down' | 'stable';
  pctChange: string;
  currentVal: number;
  prevVal: number;
}

export interface BscPerspective {
  id: string;
  label: string;
  icon: string;
  description: string;
  kpis: BscKpi[];
}

export interface BscSummary {
  score: number;
  green: number;
  yellow: number;
  red: number;
  total: number;
  label: string;
}

export interface BscViewModel {
  generatedAt: string;
  periodLabel: string;
  perspectives: BscPerspective[];
  summary: BscSummary;
}
