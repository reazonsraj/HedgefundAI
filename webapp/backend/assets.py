ASSET_PRESETS = {
    "stocks": [
        {"ticker": "AAPL", "name": "Apple Inc."},
        {"ticker": "MSFT", "name": "Microsoft"},
        {"ticker": "NVDA", "name": "NVIDIA"},
        {"ticker": "AMZN", "name": "Amazon"},
        {"ticker": "GOOGL", "name": "Alphabet"},
        {"ticker": "META", "name": "Meta Platforms"},
        {"ticker": "TSLA", "name": "Tesla"},
        {"ticker": "JPM", "name": "JPMorgan Chase"},
        {"ticker": "V", "name": "Visa"},
        {"ticker": "UNH", "name": "UnitedHealth"},
        {"ticker": "BRK.B", "name": "Berkshire Hathaway"},
        {"ticker": "JNJ", "name": "Johnson & Johnson"},
        {"ticker": "MA", "name": "Mastercard"},
        {"ticker": "PG", "name": "Procter & Gamble"},
        {"ticker": "HD", "name": "Home Depot"},
        {"ticker": "AVGO", "name": "Broadcom"},
        {"ticker": "COST", "name": "Costco"},
        {"ticker": "NFLX", "name": "Netflix"},
        {"ticker": "CRM", "name": "Salesforce"},
        {"ticker": "AMD", "name": "AMD"},
    ],
    "etfs": [
        {"ticker": "SPY", "name": "S&P 500 ETF"},
        {"ticker": "QQQ", "name": "NASDAQ-100 ETF"},
        {"ticker": "IWM", "name": "Russell 2000 ETF"},
        {"ticker": "DIA", "name": "Dow Jones ETF"},
        {"ticker": "VTI", "name": "Total Stock Market ETF"},
        {"ticker": "VOO", "name": "Vanguard S&P 500 ETF"},
        {"ticker": "ARKK", "name": "ARK Innovation ETF"},
        {"ticker": "XLF", "name": "Financial Select ETF"},
        {"ticker": "XLE", "name": "Energy Select ETF"},
        {"ticker": "XLK", "name": "Technology Select ETF"},
    ],
    "forex": [
        {"ticker": "EURUSD", "name": "EUR/USD"},
        {"ticker": "GBPUSD", "name": "GBP/USD"},
        {"ticker": "USDJPY", "name": "USD/JPY"},
        {"ticker": "USDCHF", "name": "USD/CHF"},
        {"ticker": "AUDUSD", "name": "AUD/USD"},
        {"ticker": "USDCAD", "name": "USD/CAD"},
        {"ticker": "NZDUSD", "name": "NZD/USD"},
        {"ticker": "EURGBP", "name": "EUR/GBP"},
        {"ticker": "EURJPY", "name": "EUR/JPY"},
        {"ticker": "GBPJPY", "name": "GBP/JPY"},
    ],
}


def search_assets(query: str) -> list[dict]:
    query = query.upper().strip()
    if not query:
        return []
    results = []
    for category, assets in ASSET_PRESETS.items():
        for asset in assets:
            if query in asset["ticker"] or query in asset["name"].upper():
                results.append({**asset, "category": category})
    return results
