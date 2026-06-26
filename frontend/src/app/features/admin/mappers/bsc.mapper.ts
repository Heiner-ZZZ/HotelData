import type { BscResponseDto, BscKpiDto, BscPerspectiveDto } from '../models/bsc.dto';
import type { BscViewModel, BscKpi, BscPerspective } from '../models/bsc.model';

function mapKpi(dto: BscKpiDto): BscKpi {
  return {
    label: dto.label,
    value: dto.value,
    unit: dto.unit,
    target: dto.target,
    detail: dto.detail,
    semaforo: dto.semaforo,
    trend: dto.trend,
    pctChange: dto.pct_change,
    currentVal: dto.current_val,
    prevVal: dto.prev_val,
  };
}

function mapPerspective(dto: BscPerspectiveDto): BscPerspective {
  return {
    id: dto.id,
    label: dto.label,
    icon: dto.icon,
    description: dto.description,
    kpis: dto.kpis.map(mapKpi),
  };
}

export function mapBscResponse(dto: BscResponseDto): BscViewModel {
  return {
    generatedAt: dto.generated_at,
    periodLabel: dto.period_label,
    perspectives: dto.perspectives.map(mapPerspective),
    summary: {
      score: dto.summary.score,
      green: dto.summary.green,
      yellow: dto.summary.yellow,
      red: dto.summary.red,
      total: dto.summary.total,
      label: dto.summary.label,
    },
  };
}
