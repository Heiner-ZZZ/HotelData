import type {
  Ga03ConfigDto,
  PocketbaseStatusDto,
  MongodbStatusDto,
  ServicesResponseDto,
  ReportsResponseDto,
  Ga03ProgressResponseDto,
  PipelineProgressDto,
  PreparationProgressDto,
  ExecutionStatusResponseDto,
} from '../models/monitoring.dto';
import type {
  MonitoringViewModel,
  MonitoringServicesViewModel,
  ServiceStatusCard,
  Ga03ProgressInfo,
  PipelineSection,
  ReportItem,
} from '../models/monitoring.model';

function serviceTone(
  pb: PocketbaseStatusDto,
  mongo: MongodbStatusDto,
): 'success' | 'warning' | 'error' | 'muted' {
  return pb.state === 'ready' ? 'success' : pb.state === 'incomplete' ? 'warning' : 'error';
}

function buildServiceCards(config: Ga03ConfigDto, pb: PocketbaseStatusDto, mongo: MongodbStatusDto, artifacts: ServicesResponseDto['artifacts']): ServiceStatusCard[] {
  return [
    {
      label: 'PocketBase',
      value: pb.message,
      description: `Colección: ${pb.collection} | Conteo: ${pb.count ?? 'N/D'} / ${config.target_records}`,
      tone: serviceTone(pb, mongo),
    },
    {
      label: 'MongoDB',
      value: mongo.message,
      description: `Base: ${mongo.database} | Fact GA03: ${mongo.ga03_fact_count ?? 'N/D'}`,
      tone: mongo.available ? 'success' : 'error',
    },
    {
      label: 'Parquet',
      value: artifacts.parquet.exists ? 'Generado' : 'Pendiente',
      description: artifacts.parquet.path,
      tone: artifacts.parquet.exists ? 'success' : 'warning',
    },
    {
      label: 'JSONL',
      value: artifacts.jsonl.exists ? 'Generado' : 'Pendiente',
      description: artifacts.jsonl.path,
      tone: artifacts.jsonl.exists ? 'success' : 'warning',
    },
  ];
}

function buildServicesViewModel(dto: ServicesResponseDto): MonitoringServicesViewModel {
  return {
    services: buildServiceCards(dto.config, dto.pocketbase, dto.mongodb, dto.artifacts),
    configInfo: {
      taskNumber: dto.config.task_number,
      targetRecords: dto.config.target_records,
      pbCollection: dto.config.pocketbase_collection,
      sourceCsvExists: dto.config.source_csv_exists,
      sourceCsv: dto.config.source_csv_resolved,
    },
  };
}

function buildProgressInfo(prep: PreparationProgressDto, pipe: PipelineProgressDto): Ga03ProgressInfo {
  const sections: PipelineSection[] = Object.entries(pipe.sections ?? {}).map(([key, sec]) => ({
    key,
    label: sec.label,
    complete: sec.complete,
  }));

  return {
    preparationStatus: prep.status,
    preparationPercent: prep.percent,
    preparationMessage: prep.message,
    preparationLoaded: prep.loaded_records,
    preparationTarget: prep.target_records,
    pipelineStatus: pipe.status,
    pipelinePercent: pipe.percent,
    pipelineElapsedMs: pipe.elapsed_ms,
    pipelineMessage: pipe.message,
    pipelineSections: sections,
    isRunning: prep.is_running || pipe.is_running,
  };
}

function buildReports(dto: ReportsResponseDto): ReportItem[] {
  const labels: Record<string, string> = {
    progress: 'Progreso preparación',
    pipeline_progress: 'Progreso pipeline',
    validation: 'Validación',
    quality: 'Calidad',
    execution: 'Ejecución',
  };
  return Object.entries(dto).map(([key, value]) => ({
    name: key,
    label: labels[key] || key,
    exists: value.exists,
    path: value.path,
  }));
}

export function mapMonitoringData(
  servicesDto: ServicesResponseDto,
  reportsDto: ReportsResponseDto,
  progressDto: Ga03ProgressResponseDto,
  executionDto: ExecutionStatusResponseDto,
): MonitoringViewModel {
  return {
    services: buildServicesViewModel(servicesDto),
    progress: buildProgressInfo(progressDto.preparation, progressDto.pipeline),
    reports: buildReports(reportsDto),
    execution: executionDto.available && executionDto.summary
      ? {
          available: true,
          executionId: executionDto.summary.execution_id ?? 'N/D',
          executedAt: executionDto.summary.executed_at ?? 'N/D',
          status: executionDto.summary.status ?? 'N/D',
          validRecords: executionDto.summary.valid_fact_records ?? 0,
          rejectedRecords: executionDto.summary.rejected_records ?? 0,
          sourceRows: executionDto.summary.source_rows ?? 0,
        }
      : null,
  };
}
