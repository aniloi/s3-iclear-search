/** All TypeScript interfaces for the S3 Fintrans Search UI. */

export interface SearchFormData {
  date: string;
  ids: string;
  profile: string;
  fileTypes: string[];
  bucket: string;
  contextLines: number;
}

export interface ProfileOption {
  name: string;
  resolved_bucket: string | null;
  is_known: boolean;
}

export interface MatchLineData {
  line_number: number;
  line_content: string;
}

export interface FileMatchData {
  filename: string;
  matchCount: number;
  context: string[];
}

export interface SearchResultData {
  id: string;
  found: boolean;
  totalMatchCount: number;
  files: FileMatchData[];
}

export interface SearchReportData {
  date: string;
  bucket: string;
  profile: string;
  filesSearched: number;
  filesFailed: number;
  warnings: string[];
  results: SearchResultData[];
  summary: {
    total: number;
    found: number;
    notFound: number;
  };
}

export interface AuthInfo {
  profile: string;
  account: string;
  arn: string;
}

export interface DiscoveryInfo {
  files_found: number;
  files: { filename: string; size: number }[];
}

export interface FileProgress {
  total: number;
  completed: number;
  currentFile: string | null;
  percentage: number;
}

export type TabStatus =
  | "connecting"
  | "authenticating"
  | "discovering"
  | "searching"
  | "complete"
  | "cancelled"
  | "error";

export interface SearchTab {
  id: string;
  label: string;
  status: TabStatus;
  params: SearchFormData;
  authInfo: AuthInfo | null;
  discovery: DiscoveryInfo | null;
  fileProgress: FileProgress;
  results: SearchResultData[];
  report: SearchReportData | null;
  warnings: string[];
  error: string | null;
}

export interface SearchHistoryEntry {
  search_id: string;
  date: string;
  profile: string;
  bucket: string;
  ids_count: number;
  found_count: number;
  total_ids: number;
  files_searched: number;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface SavedSearch {
  id: string;
  name: string;
  params: {
    date: string;
    ids: string[];
    profile: string;
    file_types: string[];
    bucket: string | null;
    context_lines: number;
  };
  created_at: string;
}
