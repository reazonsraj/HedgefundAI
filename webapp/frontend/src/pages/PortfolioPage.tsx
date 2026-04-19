import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { Portfolio, Analyst, ModelInfo } from "@/types";
import { useAnalysisStream } from "@/hooks/useAnalysisStream";
import { X, Play, Loader2 } from "lucide-react";

const SIGNAL_COLORS: Record<string, string> = { bullish: "text-[#22c55e]", bearish: "text-[#ef4444]", neutral: "text-[#eab308]" };
const ACTION_COLORS: Record<string, string> = { buy: "text-[#22c55e]", short: "text-[#ef4444]", hold: "text-[#eab308]", cover: "text-[#22c55e]", sell: "text-[#ef4444]" };

export function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [analysts, setAnalysts] = useState<Analyst[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedAnalysts, setSelectedAnalysts] = useState<string[]>([]);
  const [modelName, setModelName] = useState("claude-sonnet-4-6");
  const [modelProvider, setModelProvider] = useState("Anthropic");
  const [initialCash, setInitialCash] = useState(100000);
  const [marginReq, setMarginReq] = useState(0);
  const [startDate, setStartDate] = useState(() => { const d = new Date(); d.setMonth(d.getMonth() - 3); return d.toISOString().split("T")[0]; });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const stream = useAnalysisStream();

  useEffect(() => {
    api.portfolios.list().then((ps) => { if (ps.length > 0) setPortfolio(ps[0]); });
    api.analysts().then((a) => { setAnalysts(a); setSelectedAnalysts(a.map((x) => x.key)); });
    api.config.models().then(setModels);
  }, []);

  const removeTicker = async (ticker: string) => {
    if (!portfolio) return;
    const updated = await api.portfolios.update(portfolio.id, { tickers: portfolio.tickers.filter((t) => t !== ticker) });
    setPortfolio(updated);
  };

  const handleRun = () => {
    if (!portfolio || portfolio.tickers.length === 0) return;
    stream.startRun({ portfolio_id: portfolio.id, model_name: modelName, model_provider: modelProvider, selected_analysts: selectedAnalysts, start_date: startDate, end_date: endDate });
  };

  const toggleAllAnalysts = () => {
    setSelectedAnalysts(selectedAnalysts.length === analysts.length ? [] : analysts.map((a) => a.key));
  };

  const handleModelChange = (v: string) => {
    setModelName(v);
    const m = models.find((m) => m.model_name === v);
    if (m) setModelProvider(m.provider);
  };

  const modelsByProvider: Record<string, ModelInfo[]> = {};
  models.forEach((m) => { if (!modelsByProvider[m.provider]) modelsByProvider[m.provider] = []; modelsByProvider[m.provider].push(m); });

  const completedAgents = stream.events.filter((e) => e.signal);
  const agentNames = [...new Set(completedAgents.map((e) => e.agent_name))];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Portfolio</h1>
        {stream.isRunning && <div className="flex items-center gap-2 text-sm text-[#6366f1]"><Loader2 size={16} className="animate-spin" /> Analysis running...</div>}
      </div>

      {!stream.isRunning && !stream.decisions && (
        <>
          <div className="bg-[#111] border border-[#222] rounded-lg p-4 mb-4">
            <h2 className="text-sm font-medium text-[#999] mb-3">Selected Tickers</h2>
            {portfolio && portfolio.tickers.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {portfolio.tickers.map((t) => (
                  <span key={t} className="flex items-center gap-1 bg-[#1a1a1a] px-3 py-1.5 rounded-md text-sm">{t}<button onClick={() => removeTicker(t)} className="text-[#666] hover:text-[#ef4444]"><X size={14} /></button></span>
                ))}
              </div>
            ) : <p className="text-sm text-[#666]">No tickers selected. Go to Assets to add some.</p>}
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-[#111] border border-[#222] rounded-lg p-4">
              <label className="block text-xs text-[#666] mb-1">Initial Cash</label>
              <input type="number" value={initialCash} onChange={(e) => setInitialCash(Number(e.target.value))} className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]" />
            </div>
            <div className="bg-[#111] border border-[#222] rounded-lg p-4">
              <label className="block text-xs text-[#666] mb-1">Margin Requirement (%)</label>
              <input type="number" value={marginReq} onChange={(e) => setMarginReq(Number(e.target.value))} className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]" />
            </div>
            <div className="bg-[#111] border border-[#222] rounded-lg p-4">
              <label className="block text-xs text-[#666] mb-1">Start Date</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]" />
            </div>
            <div className="bg-[#111] border border-[#222] rounded-lg p-4">
              <label className="block text-xs text-[#666] mb-1">End Date</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]" />
            </div>
          </div>

          <div className="bg-[#111] border border-[#222] rounded-lg p-4 mb-4">
            <label className="block text-xs text-[#666] mb-1">Model</label>
            <select value={modelName} onChange={(e) => handleModelChange(e.target.value)} className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1]">
              {Object.entries(modelsByProvider).map(([provider, ms]) => (
                <optgroup key={provider} label={provider}>{ms.map((m) => <option key={m.model_name} value={m.model_name}>{m.display_name}</option>)}</optgroup>
              ))}
            </select>
          </div>

          <div className="bg-[#111] border border-[#222] rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs text-[#666]">Analysts</label>
              <button onClick={toggleAllAnalysts} className="text-xs text-[#6366f1] hover:underline">{selectedAnalysts.length === analysts.length ? "Deselect All" : "Select All"}</button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {analysts.map((a) => {
                const sel = selectedAnalysts.includes(a.key);
                return (
                  <button key={a.key} onClick={() => setSelectedAnalysts(sel ? selectedAnalysts.filter((k) => k !== a.key) : [...selectedAnalysts, a.key])} className={`text-left p-2 rounded-md border text-xs transition-colors ${sel ? "border-[#6366f1]/40 bg-[#6366f1]/10 text-white" : "border-[#222] text-[#666] hover:text-[#999]"}`}>
                    <div className="font-medium">{a.display_name}</div>
                    <div className="text-[#666] truncate">{a.description}</div>
                  </button>
                );
              })}
            </div>
          </div>

          <button onClick={handleRun} disabled={!portfolio || portfolio.tickers.length === 0 || selectedAnalysts.length === 0} className="w-full bg-[#6366f1] hover:bg-[#5558e6] disabled:opacity-40 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium flex items-center justify-center gap-2"><Play size={18} /> Run Analysis</button>
        </>
      )}

      {/* Error display - always visible */}
      {stream.error && !stream.isRunning && (
        <div className="mb-4">
          <div className="bg-[#ef4444]/10 border border-[#ef4444]/30 rounded-lg p-4 text-[#ef4444] text-sm mb-2">
            Error: {stream.error}
          </div>
          <button onClick={() => stream.cancel()} className="text-sm text-[#6366f1] hover:underline">Dismiss</button>
        </div>
      )}

      {/* Streaming results */}
      {(stream.isRunning || stream.decisions) && (
        <div>
          {stream.isRunning && <div className="w-full bg-[#222] rounded-full h-2 mb-6"><div className="bg-[#6366f1] h-2 rounded-full transition-all" style={{ width: `${Math.min((agentNames.length / Math.max(selectedAnalysts.length + 2, 1)) * 100, 100)}%` }} /></div>}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
            {agentNames.map((agentName) => {
              const agentEvents = completedAgents.filter((e) => e.agent_name === agentName);
              const displayName = agentName.replace(/_agent$/, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
              const isExpanded = expandedAgent === agentName;
              return (
                <button key={agentName} onClick={() => setExpandedAgent(isExpanded ? null : agentName)} className="bg-[#111] border border-[#222] rounded-lg p-4 text-left hover:border-[#333] transition-colors">
                  <div className="font-medium text-sm mb-2">{displayName}</div>
                  <div className="space-y-1">
                    {agentEvents.map((ev, i) => (
                      <div key={i} className="flex justify-between text-xs"><span className="text-[#999]">{ev.ticker}</span><span className={SIGNAL_COLORS[ev.signal || "neutral"]}>{ev.signal?.toUpperCase()} {ev.confidence ? `${Math.round(ev.confidence)}%` : ""}</span></div>
                    ))}
                  </div>
                  {isExpanded && agentEvents[0]?.reasoning && <p className="mt-3 text-xs text-[#666] border-t border-[#222] pt-3 max-h-40 overflow-y-auto">{agentEvents[0].reasoning.slice(0, 500)}{agentEvents[0].reasoning.length > 500 ? "..." : ""}</p>}
                </button>
              );
            })}
          </div>

          {stream.decisions && (
            <div className="bg-[#111] border border-[#6366f1]/30 rounded-lg p-4">
              <h2 className="text-sm font-medium text-white mb-3">Portfolio Decisions</h2>
              <div className="space-y-2">
                {Object.entries(stream.decisions).map(([ticker, d]) => (
                  <div key={ticker} className="flex items-center justify-between py-2 border-b border-[#1a1a1a] last:border-0">
                    <span className="text-white font-medium text-sm">{ticker}</span>
                    <div className="flex items-center gap-4">
                      <span className={`font-medium text-sm ${ACTION_COLORS[d.action.toLowerCase()] || "text-white"}`}>{d.action.toUpperCase()} {d.quantity}</span>
                      <span className="text-xs text-[#666]">{d.confidence}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {stream.error && <div className="bg-[#ef4444]/10 border border-[#ef4444]/30 rounded-lg p-4 text-[#ef4444] text-sm mt-4">Error: {stream.error}</div>}
          {!stream.isRunning && <button onClick={() => stream.cancel()} className="mt-4 text-sm text-[#6366f1] hover:underline">Start New Analysis</button>}
        </div>
      )}
    </div>
  );
}
