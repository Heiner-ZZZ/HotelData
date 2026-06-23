export interface ServiceStatusCard {
  label: string;
  icon: string;
  value: string;
  description: string;
  tone: 'success' | 'warning' | 'error' | 'muted';
}

export interface PipelineSection {
  key: string;
  label: string;
  complete: boolean;
}

export interface Ga03ProgressInfo {
  preparationStatus: string;
  preparationPercent: number;
  preparationMessage: string;
  preparationLoaded: number;
  preparationTarget: number;
  pipelineStatus: string;
  pipelinePercent: number;
  pipelineElapsedMs: number;
  pipelineMessage: string;
  pipelineSections: PipelineSection[];
  pipelineTarget: number;
  isRunning: boolean;
}

export interface MonitoringServicesViewModel {
  services: ServiceStatusCard[];
  configInfo: {
    taskNumber: string;
    targetRecords: number;
    targetRecordsPb: number;
    targetRecordsMongo: number;
    pbCollection: string;
    sourceCsvExists: boolean;
    sourceCsv: string;
  };
}

export interface ReportItem {
  name: string;
  label: string;
  exists: boolean;
  path: string;
}

export interface MonitoringViewModel {
  services: MonitoringServicesViewModel;
  progress: Ga03ProgressInfo;
  reports: ReportItem[];
  execution: {
    available: boolean;
    executionId: string;
    executedAt: string;
    status: string;
    validRecords: number;
    rejectedRecords: number;
    sourceRows: number;
  } | null;
}
