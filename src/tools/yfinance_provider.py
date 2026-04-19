"""Yahoo Finance fallback data provider for assets not covered by Financial Datasets API.
Supports ETFs (SPY, QQQ), indices, and forex pairs."""

import logging
from datetime import datetime

import yfinance as yf

from src.data.models import (
    CompanyNews,
    FinancialMetrics,
    InsiderTrade,
    LineItem,
    Price,
)

logger = logging.getLogger(__name__)

# Map common forex notations to yfinance format
FOREX_TICKER_MAP = {
    "EURUSD": "EURUSD=X",
    "EUR/USD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "USD/JPY": "USDJPY=X",
    "USDCHF": "USDCHF=X",
    "USD/CHF": "USDCHF=X",
    "AUDUSD": "AUDUSD=X",
    "AUD/USD": "AUDUSD=X",
    "USDCAD": "USDCAD=X",
    "USD/CAD": "USDCAD=X",
    "NZDUSD": "NZDUSD=X",
    "NZD/USD": "NZDUSD=X",
    "EURGBP": "EURGBP=X",
    "EUR/GBP": "EURGBP=X",
    "EURJPY": "EURJPY=X",
    "EUR/JPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
    "GBP/JPY": "GBPJPY=X",
}


def _to_yf_ticker(ticker: str) -> str:
    return FOREX_TICKER_MAP.get(ticker.upper(), ticker)


def _is_forex(ticker: str) -> bool:
    return ticker.upper() in FOREX_TICKER_MAP or ticker.endswith("=X")


def get_prices_yf(ticker: str, start_date: str, end_date: str) -> list[Price]:
    """Fetch price data from Yahoo Finance."""
    try:
        yf_ticker = _to_yf_ticker(ticker)
        data = yf.download(yf_ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            return []

        # Handle multi-level columns from yfinance
        if hasattr(data.columns, 'levels') and len(data.columns.levels) > 1:
            data = data.droplevel(1, axis=1)

        prices = []
        for date, row in data.iterrows():
            vol = int(row.get("Volume", 0)) if not _is_forex(ticker) else 0
            prices.append(Price(
                open=float(row["Open"]),
                close=float(row["Close"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                volume=vol,
                time=date.strftime("%Y-%m-%d"),
            ))
        return prices
    except Exception as e:
        logger.warning("yfinance price fetch failed for %s: %s", ticker, e)
        return []


def get_financial_metrics_yf(ticker: str, end_date: str, period: str = "ttm", limit: int = 10) -> list[FinancialMetrics]:
    """Fetch financial metrics from Yahoo Finance."""
    if _is_forex(ticker):
        return []

    try:
        yf_ticker = _to_yf_ticker(ticker)
        t = yf.Ticker(yf_ticker)
        info = t.info

        if not info or "symbol" not in info:
            return []

        metrics = FinancialMetrics(
            ticker=ticker,
            report_period=end_date,
            period=period,
            currency=info.get("currency", "USD"),
            market_cap=info.get("marketCap"),
            enterprise_value=info.get("enterpriseValue"),
            price_to_earnings_ratio=info.get("trailingPE"),
            price_to_book_ratio=info.get("priceToBook"),
            price_to_sales_ratio=info.get("priceToSalesTrailing12Months"),
            enterprise_value_to_ebitda_ratio=info.get("enterpriseToEbitda"),
            enterprise_value_to_revenue_ratio=info.get("enterpriseToRevenue"),
            free_cash_flow_yield=None,
            peg_ratio=info.get("pegRatio"),
            gross_margin=info.get("grossMargins"),
            operating_margin=info.get("operatingMargins"),
            net_margin=info.get("profitMargins"),
            return_on_equity=info.get("returnOnEquity"),
            return_on_assets=info.get("returnOnAssets"),
            return_on_invested_capital=None,
            asset_turnover=None,
            inventory_turnover=None,
            receivables_turnover=None,
            days_sales_outstanding=None,
            operating_cycle=None,
            working_capital_turnover=None,
            current_ratio=info.get("currentRatio"),
            quick_ratio=info.get("quickRatio"),
            cash_ratio=None,
            operating_cash_flow_ratio=None,
            debt_to_equity=info.get("debtToEquity", 0) / 100 if info.get("debtToEquity") else None,
            debt_to_assets=None,
            interest_coverage=None,
            revenue_growth=info.get("revenueGrowth"),
            earnings_growth=info.get("earningsGrowth"),
            book_value_growth=None,
            earnings_per_share_growth=None,
            free_cash_flow_growth=None,
            operating_income_growth=None,
            ebitda_growth=None,
            payout_ratio=info.get("payoutRatio"),
            earnings_per_share=info.get("trailingEps"),
            book_value_per_share=info.get("bookValue"),
            free_cash_flow_per_share=None,
        )
        return [metrics]
    except Exception as e:
        logger.warning("yfinance metrics fetch failed for %s: %s", ticker, e)
        return []


def get_market_cap_yf(ticker: str) -> float | None:
    """Fetch market cap from Yahoo Finance."""
    if _is_forex(ticker):
        return None
    try:
        yf_ticker = _to_yf_ticker(ticker)
        t = yf.Ticker(yf_ticker)
        return t.info.get("marketCap")
    except Exception:
        return None


def search_line_items_yf(ticker: str, line_items: list[str], end_date: str, period: str = "ttm", limit: int = 10) -> list[LineItem]:
    """Fetch financial line items from Yahoo Finance."""
    if _is_forex(ticker):
        return []

    try:
        yf_ticker = _to_yf_ticker(ticker)
        t = yf.Ticker(yf_ticker)

        # Gather data from income statement, balance sheet, cash flow
        financials = t.quarterly_financials if period != "annual" else t.financials
        balance = t.quarterly_balance_sheet if period != "annual" else t.balance_sheet
        cashflow = t.quarterly_cashflow if period != "annual" else t.cashflow

        # Merge all into one dict per period
        all_data = {}
        for df in [financials, balance, cashflow]:
            if df is not None and not df.empty:
                for col in df.columns:
                    date_str = col.strftime("%Y-%m-%d") if hasattr(col, 'strftime') else str(col)
                    if date_str not in all_data:
                        all_data[date_str] = {}
                    for idx in df.index:
                        key = idx.lower().replace(" ", "_")
                        val = df.loc[idx, col]
                        if val is not None and str(val) != "nan":
                            all_data[date_str][key] = float(val)

        # Filter to dates <= end_date and build LineItems
        results = []
        for date_str in sorted(all_data.keys(), reverse=True):
            if date_str > end_date:
                continue
            if len(results) >= limit:
                break

            item_data = {
                "ticker": ticker,
                "report_period": date_str,
                "period": period,
                "currency": "USD",
            }
            # Map requested line items
            available = all_data[date_str]
            for li in line_items:
                key = li.lower().replace(" ", "_")
                item_data[li] = available.get(key, available.get(li, None))

            results.append(LineItem(**item_data))

        return results
    except Exception as e:
        logger.warning("yfinance line items fetch failed for %s: %s", ticker, e)
        return []


def get_insider_trades_yf(ticker: str, end_date: str, start_date: str | None = None, limit: int = 1000) -> list[InsiderTrade]:
    """Fetch insider trades from Yahoo Finance."""
    if _is_forex(ticker):
        return []
    try:
        yf_ticker = _to_yf_ticker(ticker)
        t = yf.Ticker(yf_ticker)
        transactions = t.insider_transactions
        if transactions is None or transactions.empty:
            return []

        trades = []
        for _, row in transactions.iterrows():
            date_str = row.get("Start Date", row.get("Date", ""))
            if hasattr(date_str, 'strftime'):
                date_str = date_str.strftime("%Y-%m-%d")
            date_str = str(date_str)[:10]

            if end_date and date_str > end_date:
                continue
            if start_date and date_str < start_date:
                continue

            shares = row.get("Shares", 0)
            value = row.get("Value", 0)
            price = value / shares if shares and shares != 0 else None

            trades.append(InsiderTrade(
                ticker=ticker,
                issuer=None,
                name=str(row.get("Insider", "")),
                title=str(row.get("Position", "")),
                is_board_director=None,
                transaction_date=date_str,
                transaction_shares=float(shares) if shares else None,
                transaction_price_per_share=float(price) if price else None,
                transaction_value=float(value) if value else None,
                shares_owned_before_transaction=None,
                shares_owned_after_transaction=None,
                security_title=row.get("Text", None),
                filing_date=date_str,
            ))
        return trades[:limit]
    except Exception as e:
        logger.warning("yfinance insider trades fetch failed for %s: %s", ticker, e)
        return []


def get_company_news_yf(ticker: str, end_date: str, start_date: str | None = None, limit: int = 50) -> list[CompanyNews]:
    """Fetch company news from Yahoo Finance."""
    try:
        yf_ticker = _to_yf_ticker(ticker)
        t = yf.Ticker(yf_ticker)
        news = t.news
        if not news:
            return []

        results = []
        for item in news[:limit]:
            date_str = datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d") if item.get("providerPublishTime") else ""
            # Newer yfinance versions use different keys
            pub_date = item.get("content", {}).get("pubDate", date_str) if isinstance(item.get("content"), dict) else date_str

            title = item.get("title", item.get("content", {}).get("title", "")) if isinstance(item.get("content"), dict) else item.get("title", "")
            source = item.get("publisher", item.get("content", {}).get("provider", {}).get("displayName", "Unknown")) if isinstance(item.get("content"), dict) else item.get("publisher", "Unknown")
            url = item.get("link", item.get("content", {}).get("canonicalUrl", {}).get("url", "")) if isinstance(item.get("content"), dict) else item.get("link", "")

            results.append(CompanyNews(
                ticker=ticker,
                title=str(title),
                source=str(source),
                date=str(pub_date)[:10] if pub_date else "",
                url=str(url),
            ))
        return results
    except Exception as e:
        logger.warning("yfinance news fetch failed for %s: %s", ticker, e)
        return []
