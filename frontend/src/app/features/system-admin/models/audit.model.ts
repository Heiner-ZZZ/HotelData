export interface EtlExecutionItem {
  executionId: string;
  executedAtLabel: string;
  status: string;
}

export interface SearchLogItem {
  query: string;
  destination: string;
  country: string;
  searchedAtLabel: string;
}

export interface AuditViewModel {
  totalExecutions: number;
  totalSearches: number;
  etlExecutions: EtlExecutionItem[];
  searchLogs: SearchLogItem[];
}
