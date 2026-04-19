const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  assets: {
    presets: () => request<import("@/types").AssetPresets>("/assets/presets"),
    search: (q: string) => request<import("@/types").Asset[]>(`/assets/search?q=${q}`),
  },
  portfolios: {
    list: () => request<import("@/types").Portfolio[]>("/portfolios"),
    create: (data: { name: string; tickers: string[]; initial_cash: number; margin_requirement: number }) =>
      request<import("@/types").Portfolio>("/portfolios", { method: "POST", body: JSON.stringify(data) }),
    get: (id: number) => request<import("@/types").Portfolio>(`/portfolios/${id}`),
    update: (id: number, data: Partial<{ name: string; tickers: string[]; initial_cash: number; margin_requirement: number }>) =>
      request<import("@/types").Portfolio>(`/portfolios/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => request<{ status: string }>(`/portfolios/${id}`, { method: "DELETE" }),
  },
  analysis: {
    run: (data: { portfolio_id: number; model_name: string; model_provider: string; selected_analysts: string[]; start_date: string; end_date: string }) =>
      request<{ run_id: number }>("/analysis/run", { method: "POST", body: JSON.stringify(data) }),
    history: () => request<import("@/types").AnalysisRun[]>("/analysis/history"),
    get: (id: number) => request<import("@/types").AnalysisRun>(`/analysis/${id}`),
    streamUrl: (runId: number) => `${BASE}/analysis/stream/${runId}`,
  },
  config: {
    models: () => request<import("@/types").ModelInfo[]>("/config/models"),
    apiKeys: () => request<import("@/types").ApiKeyStatus[]>("/config/api-keys"),
    updateApiKeys: (keys: Record<string, string>) =>
      request<{ status: string }>("/config/api-keys", { method: "PUT", body: JSON.stringify({ keys }) }),
  },
  analysts: () => request<import("@/types").Analyst[]>("/analysts"),
};
