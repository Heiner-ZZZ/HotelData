export interface BscKpiDto {
  label: string;
  value: string;
  unit: string;
  target: string;
  detail: string;
  semaforo: 'green' | 'yellow' | 'red';
  trend: 'up' | 'down' | 'stable';
  pct_change: string;
  current_val: number;
  prev_val: number;
}

export interface BscPerspectiveDto {
  id: string;
  label: string;
  icon: string;
  description: string;
  kpis: BscKpiDto[];
}

export interface BscSummaryDto {
  score: number;
  green: number;
  yellow: number;
  red: number;
  total: number;
  label: string;
}

export interface BscResponseDto {
  generated_at: string;
  period_label: string;
  perspectives: BscPerspectiveDto[];
  summary: BscSummaryDto;
}
