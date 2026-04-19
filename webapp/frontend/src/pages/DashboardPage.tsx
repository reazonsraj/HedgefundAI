import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { AnalysisRun, Portfolio } from "@/types";
import { useNavigate } from "react-router-dom";

const ACTION_COLORS: Record<string, string> = {
  buy: "text-[#22c55e]", short: "text-[#ef4444]", hold: "text-[#eab308]",
  cover: "text-[#22c55e]", sell: "text-[#ef4444]",
};

export function DashboardPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [lastRun, setLastRun] = useState<AnalysisRun | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.portfolios.list().then((ps) => ps.length > 0 && setPortfolio(ps[0]));
    api.analysis.history().then((runs) => {
      if (runs.length > 0) api.analysis.get(runs[0].id).then(setLastRun);
    });
  }, []);

  const decisions = lastRun?.decisions || {};
  const decisionList = Object.entries(decisions);
  const buys = decisionList.filter(([, d]) => d.action.toLowerCase() === "buy").length;
  const shorts = decisionList.filter(([, d]) => d.action.toLowerCase() === "short").length;
  const holds = decisionList.filter(([, d]) => d.action.toLowerCase() === "hold").length;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="text-xs text-[#666] mb-1">PORTFOLIO VALUE</div>
          <div className="text-xl font-semibold">${(portfolio?.initial_cash || 100000).toLocaleString()}</div>
        </div>
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="text-xs text-[#666] mb-1">POSITIONS</div>
          <div className="text-xl font-semibold">{portfolio?.tickers.length || 0}</div>
        </div>
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="text-xs text-[#666] mb-1">LAST RUN</div>
          <div className="text-xl font-semibold">{lastRun ? new Date(lastRun.created_at).toLocaleDateString() : "None"}</div>
        </div>
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="text-xs text-[#666] mb-1">SIGNALS</div>
          <div className="text-xl font-semibold">
            {lastRun ? (<span><span className="text-[#22c55e]">{buys} Buy</span>{" / "}<span className="text-[#ef4444]">{shorts} Short</span>{holds > 0 && <span className="text-[#eab308]"> / {holds} Hold</span>}</span>) : "—"}
          </div>
        </div>
      </div>
      {lastRun && decisionList.length > 0 ? (
        <div className="bg-[#111] border border-[#222] rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-[#999]">Latest Analysis — {lastRun.model_provider} / {lastRun.model_name}</h2>
            <span className="text-xs text-[#666]">{new Date(lastRun.created_at).toLocaleString()}</span>
          </div>
          <div className="space-y-2">
            {decisionList.map(([ticker, d]) => (
              <div key={ticker} className="flex items-center justify-between py-2 border-b border-[#1a1a1a] last:border-0">
                <span className="text-white font-medium">{ticker}</span>
                <div className="flex items-center gap-4">
                  <span className={`font-medium ${ACTION_COLORS[d.action.toLowerCase()] || "text-white"}`}>{d.action.toUpperCase()} {d.quantity}</span>
                  <span className="text-xs text-[#666]">{d.confidence}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-[#111] border border-[#222] rounded-lg p-8 text-center">
          <p className="text-[#666] mb-4">No analysis runs yet.</p>
          <button onClick={() => navigate("/portfolio")} className="bg-[#6366f1] hover:bg-[#5558e6] text-white px-6 py-2 rounded-lg text-sm">Run Your First Analysis</button>
        </div>
      )}
    </div>
  );
}
