import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { AnalysisRun } from "@/types";

const STATUS_COLORS: Record<string, string> = { completed: "text-[#22c55e]", failed: "text-[#ef4444]", running: "text-[#eab308]", pending: "text-[#666]" };
const ACTION_COLORS: Record<string, string> = { buy: "text-[#22c55e]", short: "text-[#ef4444]", hold: "text-[#eab308]", cover: "text-[#22c55e]", sell: "text-[#ef4444]" };

export function HistoryPage() {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [detail, setDetail] = useState<AnalysisRun | null>(null);

  useEffect(() => { api.analysis.history().then(setRuns); }, []);

  const expand = async (id: number) => {
    if (expanded === id) { setExpanded(null); setDetail(null); return; }
    setExpanded(id);
    setDetail(await api.analysis.get(id));
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">History</h1>
      {runs.length === 0 ? <p className="text-[#666]">No analysis runs yet.</p> : (
        <div className="space-y-2">
          {runs.map((run) => {
            const decisions = run.decisions || {};
            const dl = Object.entries(decisions);
            const summary = dl.map(([, d]) => d.action.toLowerCase());
            const buys = summary.filter((a) => a === "buy").length;
            const shorts = summary.filter((a) => a === "short").length;
            const holds = summary.filter((a) => a === "hold").length;
            return (
              <div key={run.id}>
                <button onClick={() => expand(run.id)} className="w-full bg-[#111] border border-[#222] rounded-lg p-4 text-left hover:border-[#333] transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-white">{new Date(run.created_at).toLocaleString()}</span>
                      <span className="text-xs text-[#666]">{run.tickers.join(", ")}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-xs text-[#666]">{run.model_provider}/{run.model_name}</span>
                      {run.status === "completed" && <span className="text-xs"><span className="text-[#22c55e]">{buys}B</span> / <span className="text-[#ef4444]">{shorts}S</span> / <span className="text-[#eab308]">{holds}H</span></span>}
                      <span className={`text-xs ${STATUS_COLORS[run.status]}`}>{run.status}</span>
                    </div>
                  </div>
                </button>
                {expanded === run.id && detail && (
                  <div className="bg-[#0a0a0a] border border-[#222] border-t-0 rounded-b-lg p-4 space-y-4">
                    {detail.decisions && (
                      <div>
                        <h3 className="text-xs text-[#666] mb-2">DECISIONS</h3>
                        {Object.entries(detail.decisions).map(([ticker, d]) => (
                          <div key={ticker} className="flex justify-between py-1 text-sm"><span>{ticker}</span><span className={ACTION_COLORS[d.action.toLowerCase()] || "text-white"}>{d.action.toUpperCase()} {d.quantity} ({d.confidence}%)</span></div>
                        ))}
                      </div>
                    )}
                    {detail.results && detail.results.length > 0 && (
                      <div>
                        <h3 className="text-xs text-[#666] mb-2">AGENT SIGNALS</h3>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {detail.results.map((r) => (
                            <div key={r.id} className="bg-[#111] border border-[#222] rounded p-2 text-xs">
                              <div className="flex justify-between">
                                <span className="text-[#999]">{r.agent_name.replace(/_agent$/, "").replace(/_/g, " ")}</span>
                                <span className={r.signal === "bullish" ? "text-[#22c55e]" : r.signal === "bearish" ? "text-[#ef4444]" : "text-[#eab308]"}>{r.ticker}: {r.signal}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
