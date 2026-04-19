import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { AssetPresets, Portfolio } from "@/types";
import { Search, Plus, Check } from "lucide-react";

const TABS = [
  { key: "stocks" as const, label: "Stocks" },
  { key: "etfs" as const, label: "ETFs / Indices" },
  { key: "forex" as const, label: "Forex" },
];

export function AssetsPage() {
  const [presets, setPresets] = useState<AssetPresets | null>(null);
  const [tab, setTab] = useState<"stocks" | "etfs" | "forex">("stocks");
  const [search, setSearch] = useState("");
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [customTicker, setCustomTicker] = useState("");

  useEffect(() => {
    api.assets.presets().then(setPresets);
    api.portfolios.list().then((ps) => {
      if (ps.length > 0) setPortfolio(ps[0]);
      else api.portfolios.create({ name: "My Portfolio", tickers: [], initial_cash: 100000, margin_requirement: 0 }).then(setPortfolio);
    });
  }, []);

  const assets = presets ? presets[tab] : [];
  const filtered = search ? assets.filter((a) => a.ticker.includes(search.toUpperCase()) || a.name.toUpperCase().includes(search.toUpperCase())) : assets;
  const inPortfolio = new Set(portfolio?.tickers || []);

  const toggleTicker = async (ticker: string) => {
    if (!portfolio) return;
    const newTickers = inPortfolio.has(ticker) ? portfolio.tickers.filter((t) => t !== ticker) : [...portfolio.tickers, ticker];
    const updated = await api.portfolios.update(portfolio.id, { tickers: newTickers });
    setPortfolio(updated);
  };

  const addCustom = async () => {
    const ticker = customTicker.trim().toUpperCase();
    if (!ticker || !portfolio || inPortfolio.has(ticker)) return;
    const updated = await api.portfolios.update(portfolio.id, { tickers: [...portfolio.tickers, ticker] });
    setPortfolio(updated);
    setCustomTicker("");
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Assets</h1>
        <span className="text-sm text-[#666]">{portfolio?.tickers.length || 0} in portfolio</span>
      </div>
      <div className="flex gap-1 mb-4">
        {TABS.map(({ key, label }) => (
          <button key={key} onClick={() => setTab(key)} className={`px-4 py-2 rounded-md text-sm transition-colors ${tab === key ? "bg-[#1a1a1a] text-white" : "text-[#666] hover:text-[#999]"}`}>{label}</button>
        ))}
      </div>
      <div className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#666]" size={16} />
          <input type="text" placeholder="Search tickers..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-[#111] border border-[#222] rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-[#666] focus:outline-none focus:border-[#6366f1]" />
        </div>
        <div className="flex gap-1">
          <input type="text" placeholder="Custom ticker" value={customTicker} onChange={(e) => setCustomTicker(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addCustom()} className="bg-[#111] border border-[#222] rounded-lg px-3 py-2.5 text-sm text-white placeholder-[#666] focus:outline-none focus:border-[#6366f1] w-36" />
          <button onClick={addCustom} className="bg-[#6366f1] hover:bg-[#5558e6] text-white px-3 py-2 rounded-lg text-sm">Add</button>
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {filtered.map((asset) => {
          const added = inPortfolio.has(asset.ticker);
          return (
            <button key={asset.ticker} onClick={() => toggleTicker(asset.ticker)} className={`flex items-center justify-between p-3 rounded-lg border text-left transition-colors ${added ? "bg-[#6366f1]/10 border-[#6366f1]/40" : "bg-[#111] border-[#222] hover:border-[#333]"}`}>
              <div>
                <div className="text-white text-sm font-medium">{asset.ticker}</div>
                <div className="text-[#666] text-xs truncate max-w-[120px]">{asset.name}</div>
              </div>
              {added ? <Check size={16} className="text-[#6366f1] shrink-0" /> : <Plus size={16} className="text-[#666] shrink-0" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
