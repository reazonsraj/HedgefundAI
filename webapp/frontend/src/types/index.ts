export interface Asset {
  ticker: string;
  name: string;
  category?: string;
}

export interface AssetPresets {
  stocks: Asset[];
  etfs: Asset[];
  forex: Asset[];
}

export interface Portfolio {
  id: number;
  name: string;
  tickers: string[];
  initial_cash: number;
  margin_requirement: number;
  created_at: string;
  updated_at: string;
}

export interface Analyst {
  key: string;
  display_name: string;
  description: string;
  order: number;
}

export interface ModelInfo {
  display_name: string;
  model_name: string;
  provider: string;
}

export interface AnalysisResult {
  id: number;
  run_id: number;
  agent_name: string;
  ticker: string;
  signal: "bullish" | "bearish" | "neutral";
  confidence: number;
  reasoning: string;
  raw_data: Record<string, unknown>;
}

export interface AnalysisRun {
  id: number;
  portfolio_id: number;
  model_name: string;
  model_provider: string;
  selected_analysts: string[];
  tickers: string[];
  start_date: string;
  end_date: string;
  status: "pending" | "running" | "completed" | "failed";
  decisions: Record<string, { action: string; quantity: number; confidence: number; reasoning: string }> | null;
  created_at: string;
  completed_at: string | null;
  results?: AnalysisResult[];
}

export interface ApiKeyStatus {
  provider: string;
  env_var: string;
  is_set: boolean;
}
